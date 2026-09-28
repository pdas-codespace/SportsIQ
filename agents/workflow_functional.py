"""Functional workflow orchestrator using Microsoft Agent Framework @workflow/@step.

Flow:
  EngagementMonitor -> OfferGenerator -> Guardrail -> HITL approvals -> OfferApprover
  - set_approval_decision(run_id, offer_id, approved, reason)
  - start(run_id, fan_id, game_id, event_emitter, ...)
  - get_state(run_id)
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Callable
from typing import Any

from azure.identity import DefaultAzureCredential
from agent_framework import RunContext, WorkflowRunState, step, workflow

from agents.engagement_monitor import agent_def as monitor_def
from agents.middleware.policy_guardrail import validate_offers as guardrail_validate_offers
from agents.offer_approver import agent_def as approver_def
from agents.offer_approver import checkpoint
from agents.offer_generator import agent_def as generator_def
from agents.shared import config

log = logging.getLogger(__name__)

# HITL state keyed by "{run_id}:{offer_id}".
_approval_events: dict[str, asyncio.Event] = {}
_approval_decisions: dict[str, dict[str, Any]] = {}


def set_approval_decision(run_id: str, offer_id: str, approved: bool, reason: str = "") -> None:
    """Called by server endpoints when a human decision is submitted."""
    key = f"{run_id}:{offer_id}"
    _approval_decisions[key] = {"approved": approved, "reason": reason}
    event = _approval_events.get(key)
    if event:
        event.set()
    else:
        log.warning("set_approval_decision: no pending event for key=%s", key)


def _register_approval_events(run_id: str, offer_ids: list[str]) -> None:
    for offer_id in offer_ids:
        key = f"{run_id}:{offer_id}"
        event = _approval_events.get(key)
        if event is None:
            event = asyncio.Event()
            _approval_events[key] = event
        if key in _approval_decisions:
            event.set()


def _extract_json(text: str) -> str:
    start = min((text.find(c) for c in ["{", "["] if c in text), default=0)
    end = max(text.rfind("}"), text.rfind("]")) + 1
    return text[start:end] if end > start else text


@step
async def _run_engagement_monitor_step(fan_id: str, game_id: str) -> dict[str, Any]:
    # Strategy pattern: this step encapsulates monitor-agent execution independently.
    credential = DefaultAzureCredential()
    agent = monitor_def.create_agent(credential)
    prompt = (
        f"Check engagement for fan_id={fan_id}, game_id={game_id}. "
        "Should we generate offers right now?"
    )
    response = await agent.run(prompt)
    text = response.text or ""
    try:
        return json.loads(_extract_json(text))
    except Exception:
        return {"should_generate_offers": False, "reason": text}


@step
async def _run_offer_generator_step(
    fan_id: str,
    game_id: str,
    monitor_data: dict[str, Any],
    section_id: str,
    fan_name: str,
    fan_loyalty_tier: str,
    sport_context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    credential = DefaultAzureCredential()
    agent = generator_def.create_agent(credential)
    prompt = generator_def.build_offer_generation_prompt(
        fan_id=fan_id,
        game_id=game_id,
        section_id=section_id,
        stadium_id=config.DEMO_STADIUM_ID,
        monitor_data=monitor_data,
        fan_name=fan_name,
        fan_loyalty_tier=fan_loyalty_tier,
        sport_context=sport_context,
    )
    response = await agent.run(prompt)
    text = response.text or ""

    try:
        payload = json.loads(_extract_json(text))
        offers = payload.get("offers", [])
    except Exception:
        offers = []

    for offer in offers:
        if not offer.get("id"):
            offer["id"] = f"offer_{uuid.uuid4().hex[:8]}"
    return offers


@step
async def _run_offer_approver_step(
    fan_id: str,
    game_id: str,
    fan_name: str,
    fan_loyalty_tier: str,
    fan_email: str,
    offers: list[dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
) -> str:
    credential = DefaultAzureCredential()
    agent = approver_def.create_agent(credential)

    approved_items = [
        {
            **offer,
            "fan_email": fan_email,
            "fan_name": fan_name,
            "loyalty_tier": fan_loyalty_tier,
        }
        for offer in offers
        if decisions.get(offer["id"], {}).get("approved")
    ]
    rejected_items = [
        {
            "offer_id": offer["id"],
            "fan_id": fan_id,
            "game_id": game_id,
            "rejection_reason": decisions.get(offer["id"], {}).get("reason", "rejected"),
        }
        for offer in offers
        if not decisions.get(offer["id"], {}).get("approved")
    ]

    parts: list[str] = [
        "Process EVERY item below. Do not skip any. The decisions are final; execute them."
    ]
    if approved_items:
        parts.append(
            f"APPROVED — call send_fan_notification() for each of these {len(approved_items)} offer(s):\n"
            + json.dumps(approved_items, indent=2)
        )
    if rejected_items:
        parts.append(
            f"REJECTED — call log_rejection() for each of these {len(rejected_items)} offer(s):\n"
            + json.dumps(rejected_items, indent=2)
        )
    parts.append(
        f"After processing all offers, call post_teams_summary() for fan '{fan_name}', game '{game_id}'."
    )

    response = await agent.run("\n\n".join(parts))
    return response.text or ""


def _apply_policy_guardrails(
    offers: list[dict[str, Any]],
    monitor_data: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    game_state = {
        "gameExcitementIndex": monitor_data.get("gameExcitementIndex") or monitor_data.get("engagement_score"),
        "quarter": monitor_data.get("quarter"),
        "isRedZone": monitor_data.get("isRedZone"),
        "lastPlayType": monitor_data.get("lastPlayType"),
        "timeSinceScore": monitor_data.get("timeSinceScore") or monitor_data.get("timeSinceTD"),
        "down": monitor_data.get("down"),
        "scoreDifferential": monitor_data.get("scoreDifferential"),
        "gameClockQ2LessThan2m30s": monitor_data.get("gameClockQ2LessThan2m30s"),
        "activeIncident": monitor_data.get("activeIncident"),
    }
    fan_state = {
        "loyaltyTier": monitor_data.get("loyalty_tier", "Bronze"),
        "minutesSinceLastOffer": monitor_data.get("minutesSinceLastOffer"),
        "totalOffersThisGame": monitor_data.get("totalOffersThisGame", 0),
        "totalOfferValueThisGame": monitor_data.get("totalOfferValueThisGame", 0.0),
    }

    result = guardrail_validate_offers(offers, game_state, fan_state, sport=config.SPORTS_IQ_SPORT)
    return result.clean_offers, result.suppressed_offers


@workflow(name="sportsiq-functional-workflow")
async def _sportsiq_workflow(payload: dict[str, Any], ctx: RunContext) -> dict[str, Any]:
    fan_id = payload["fan_id"]
    game_id = payload["game_id"]
    fan_name = payload["fan_name"]
    fan_loyalty_tier = payload["fan_loyalty_tier"]
    fan_email = payload["fan_email"]
    section_id = payload.get("preferred_section_id") or config.DEMO_SECTION_ID
    sport_context = payload.get("sport_context") or config.default_sport_context()

    monitor_data = await _run_engagement_monitor_step(fan_id, game_id)
    if not monitor_data.get("should_generate_offers", False):
        return {
            "status": "suppressed",
            "reason": monitor_data.get("reason", "engagement or fatigue guard suppressed offers"),
            "monitor_output": monitor_data,
            "offers": [],
            "decisions": {},
            "suppressed_offers": [],
            "approver_output": "",
        }

    offers = await _run_offer_generator_step(
        fan_id,
        game_id,
        monitor_data,
        section_id,
        fan_name,
        fan_loyalty_tier,
        sport_context,
    )
    if not offers:
        return {
            "status": "suppressed",
            "reason": "Offer generation failed — no offers returned by agent.",
            "monitor_output": monitor_data,
            "offers": [],
            "decisions": {},
            "suppressed_offers": [],
            "approver_output": "",
        }

    clean_offers, suppressed_offers = _apply_policy_guardrails(offers, monitor_data)
    if not clean_offers:
        return {
            "status": "suppressed",
            "reason": "All generated offers were suppressed by policy guardrails.",
            "monitor_output": monitor_data,
            "offers": [],
            "decisions": {},
            "suppressed_offers": suppressed_offers,
            "approver_output": "",
        }

    decisions: dict[str, dict[str, Any]] = {}
    for offer in clean_offers:
        request_payload = {"offer_id": offer["id"], "offer": offer}
        decision = await ctx.request_info(
            request_payload,
            response_type=dict,
            request_id=f"approval:{offer['id']}",
        )
        decisions[offer["id"]] = {
            "approved": bool(decision.get("approved")),
            "reason": str(decision.get("reason", "")),
        }

    approver_output = await _run_offer_approver_step(
        fan_id=fan_id,
        game_id=game_id,
        fan_name=fan_name,
        fan_loyalty_tier=fan_loyalty_tier,
        fan_email=fan_email,
        offers=clean_offers,
        decisions=decisions,
    )

    return {
        "status": "completed",
        "reason": "",
        "monitor_output": monitor_data,
        "offers": clean_offers,
        "decisions": decisions,
        "suppressed_offers": suppressed_offers,
        "approver_output": approver_output,
    }


def _get_request_payload(event: Any) -> dict[str, Any]:
    payload = getattr(event, "data", None)
    if isinstance(payload, dict):
        return payload
    payload = getattr(event, "request_data", None)
    if isinstance(payload, dict):
        return payload
    return {}


async def _wait_for_decisions(run_id: str, offer_ids: list[str]) -> dict[str, dict[str, Any]]:
    tasks = []

    async def _wait_one(offer_id: str) -> tuple[str, dict[str, Any]]:
        key = f"{run_id}:{offer_id}"
        event = _approval_events.get(key)
        if event is None:
            event = asyncio.Event()
            _approval_events[key] = event
        if key in _approval_decisions:
            event.set()
        await asyncio.wait_for(event.wait(), timeout=600.0)
        return offer_id, _approval_decisions.get(key, {"approved": False, "reason": "timeout"})

    for oid in offer_ids:
        tasks.append(_wait_one(oid))

    results = await asyncio.gather(*tasks)
    return {oid: decision for oid, decision in results}


async def start(
    run_id: str,
    fan_id: str,
    game_id: str,
    event_emitter: Callable[[str, dict], None],
    fan_name: str | None = None,
    fan_loyalty_tier: str | None = None,
    fan_email: str | None = None,
    preferred_section_id: str | None = None,
    sport_context: dict[str, Any] | None = None,
) -> None:
    """Run the functional workflow and bridge HITL to existing approval endpoints."""

    def emit(event_type: str, payload: dict[str, Any]) -> None:
        try:
            event_emitter(event_type, {"run_id": run_id, **payload})
        except Exception as exc:
            log.error("event_emitter error: %s", exc)

    state: dict[str, Any] = {
        "run_id": run_id,
        "fan_id": fan_id,
        "game_id": game_id,
        "fan_name": fan_name or config.DEMO_FAN_NAME,
        "fan_loyalty_tier": fan_loyalty_tier or "Gold",
        "fan_email": fan_email or config.DEMO_FAN_EMAIL,
        "preferred_section_id": preferred_section_id or config.DEMO_SECTION_ID,
        "sport_context": sport_context or config.default_sport_context(),
        "workflow_status": "started",
    }
    checkpoint.save(run_id, state)

    emit("run_started", {"fan_id": fan_id, "game_id": game_id})
    emit("text_message", {"text": "Starting functional Sports-IQ workflow..."})

    payload = {
        "fan_id": fan_id,
        "game_id": game_id,
        "fan_name": state["fan_name"],
        "fan_loyalty_tier": state["fan_loyalty_tier"],
        "fan_email": state["fan_email"],
        "preferred_section_id": state["preferred_section_id"],
        "sport_context": state["sport_context"],
    }

    try:
        result = await _sportsiq_workflow.run(payload)

        while result.get_final_state() == WorkflowRunState.IDLE_WITH_PENDING_REQUESTS:
            requests = result.get_request_info_events()
            if not requests:
                break

            pending_requests: list[tuple[Any, str, str, dict[str, Any]]] = []
            for req in requests:
                req_id = getattr(req, "request_id", "")
                req_payload = _get_request_payload(req)
                offer_id = req_payload.get("offer_id")
                offer = req_payload.get("offer")
                if not offer_id:
                    if isinstance(req_id, str) and req_id.startswith("approval:"):
                        offer_id = req_id.split(":", 1)[1]
                if not offer_id:
                    continue
                pending_requests.append((req, req_id, offer_id, offer or {"id": offer_id}))

            offer_ids = [offer_id for _, _, offer_id, _ in pending_requests]

            if not offer_ids:
                break

            _register_approval_events(run_id, offer_ids)
            offers = [offer for _, _, _, offer in pending_requests]
            state["offers"] = offers
            state["pending_offers"] = offer_ids
            state["workflow_status"] = "awaiting_approval"
            checkpoint.save(run_id, state)

            emit("state_snapshot", {"offers": offers, "workflow_status": "awaiting_approval"})
            emit("text_message", {
                "text": f"📋 {len(offer_ids)} offers generated. Awaiting human review…"
            })
            for _, _, offer_id, offer in pending_requests:
                emit("approval_required", {"offer_id": offer_id, "offer": offer})

            decisions = await _wait_for_decisions(run_id, offer_ids)
            state["approval_decisions"] = {
                **state.get("approval_decisions", {}),
                **decisions,
            }
            checkpoint.save(run_id, state)

            responses: dict[str, dict[str, Any]] = {}
            for _, req_id, offer_id, _ in pending_requests:
                if not req_id:
                    continue
                if offer_id and offer_id in decisions:
                    responses[req_id] = decisions[offer_id]
                    decision = decisions[offer_id]
                    emit(
                        "text_message",
                        {"text": f"{'✅' if decision.get('approved') else '❌'} {offer_id} {'approved' if decision.get('approved') else 'rejected'}."},
                    )

            result = await _sportsiq_workflow.run(responses=responses)

        outputs = result.get_outputs()
        if not outputs:
            raise RuntimeError("Functional workflow completed with no output payload.")

        final_output = outputs[-1]
        workflow_status = final_output.get("status", "suppressed")

        state["monitor_output"] = final_output.get("monitor_output", {})
        state["offers"] = final_output.get("offers", [])
        state["suppressed_offers"] = final_output.get("suppressed_offers", [])
        state["approval_decisions"] = final_output.get("decisions", {})
        state["approver_output"] = final_output.get("approver_output", "")
        state["pending_offers"] = []
        state["workflow_status"] = "completed" if workflow_status == "completed" else "suppressed"
        checkpoint.save(run_id, state)

        if workflow_status == "completed":
            emit("state_snapshot", {
                "offers": state["offers"],
                "decisions": state["approval_decisions"],
                "workflow_status": "completed",
            })
            emit("run_finished", {"status": "completed"})
        else:
            reason = final_output.get("reason", "offers suppressed")
            emit("text_message", {"text": f"⛔ Offers suppressed: {reason}"})
            emit("run_finished", {"status": "suppressed"})

    except Exception as exc:
        log.exception("Functional workflow failed for run_id=%s", run_id)
        state["workflow_status"] = "failed"
        state["error"] = str(exc)
        checkpoint.save(run_id, state)
        emit("run_error", {"error": str(exc)})
        emit("run_finished", {"status": "failed"})
    finally:
        # Cleanup any lingering approval state for this run.
        keys = [k for k in list(_approval_events.keys()) if k.startswith(f"{run_id}:")]
        for key in keys:
            _approval_events.pop(key, None)
            _approval_decisions.pop(key, None)


def get_state(run_id: str) -> dict[str, Any] | None:
    return checkpoint.load(run_id)
