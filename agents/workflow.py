"""
Async workflow orchestrator — EngagementMonitor → OfferGenerator → [HITL] → OfferApprover.

Uses Microsoft Agent Framework (agent-framework-core + agent-framework-foundry).
HITL is implemented via asyncio.Event: workflow awaits per-offer events that are
resolved by POST /api/run/{id}/tool-result from the browser approval UI.

Usage:
    # Start workflow as a background asyncio task
    asyncio.create_task(workflow.start(run_id, fan_id, game_id, event_emitter))

    # From the HTTP tool-result endpoint:
    workflow.set_approval_decision(run_id, offer_id, approved, reason)
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Callable

from azure.identity import DefaultAzureCredential

from agents.shared import config, telemetry
from agents.offer_approver import checkpoint
from agents.engagement_monitor import agent_def as monitor_def
from agents.offer_generator import agent_def as generator_def
from agents.offer_approver import agent_def as approver_def
from agents.middleware.policy_guardrail import validate_offers as guardrail_validate_offers

log = logging.getLogger(__name__)

# ── HITL state ────────────────────────────────────────────────────────────────
# Keyed by "{run_id}:{offer_id}". Set by set_approval_decision(), awaited in start().
_approval_events: dict[str, asyncio.Event] = {}
_approval_decisions: dict[str, dict] = {}


def set_approval_decision(run_id: str, offer_id: str, approved: bool, reason: str = "") -> None:
    """Called by server.py when the browser posts a tool-result. Thread-safe."""
    key = f"{run_id}:{offer_id}"
    _approval_decisions[key] = {"approved": approved, "reason": reason}
    event = _approval_events.get(key)
    if event:
        event.set()
    else:
        log.warning("set_approval_decision: no pending event for key=%s", key)


async def start(
    run_id: str,
    fan_id: str,
    game_id: str,
    event_emitter: Callable[[str, dict], None],
    fan_name: str | None = None,
    fan_loyalty_tier: str | None = None,
    fan_email: str | None = None,
    preferred_section_id: str | None = None,
    sport_context: dict | None = None,
) -> None:
    """
    Main async workflow coroutine. Must be launched with asyncio.create_task().
    Emits AG-UI events via event_emitter(event_type, payload).
    Pauses at HITL points until set_approval_decision() is called for each offer.
    """
    from opentelemetry import trace as otel_trace
    tracer = otel_trace.get_tracer("sports-iq.workflow")

    credential = DefaultAzureCredential()

    def emit(event_type: str, payload: dict) -> None:
        try:
            event_emitter(event_type, {"run_id": run_id, **payload})
        except Exception as exc:
            log.error("event_emitter error: %s", exc)

    with tracer.start_as_current_span("sportsiq-workflow.run") as root_span:
        root_span.set_attribute("workflow.run_id", run_id)
        root_span.set_attribute("workflow.fan_id", fan_id)
        root_span.set_attribute("workflow.game_id", game_id)

        state: dict = {
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

        # ── Step 1: Engagement Monitor ────────────────────────────────────────────
        emit("text_message", {"text": "🔍 Checking engagement score and offer fatigue gate…"})
        emit("tool_call_start", {"tool": "EngagementMonitorAgent"})

        with tracer.start_as_current_span("workflow.engagement_monitor") as mon_span:
            mon_span.set_attribute("workflow.fan_id", fan_id)
            monitor_agent = monitor_def.create_agent(credential)
            monitor_prompt = (
                f"Check engagement for fan_id={fan_id}, game_id={game_id}. "
                "Should we generate offers right now?"
            )
            monitor_response = await monitor_agent.run(monitor_prompt)
            monitor_text = monitor_response.text or ""
            mon_span.set_attribute("workflow.monitor_response_length", len(monitor_text))

        emit("tool_call_end", {"tool": "EngagementMonitorAgent", "output": monitor_text[:200]})

        try:
            monitor_data = json.loads(_extract_json(monitor_text))
        except Exception:
            monitor_data = {"should_generate_offers": False, "reason": monitor_text}

        root_span.set_attribute("workflow.should_generate_offers",
                                monitor_data.get("should_generate_offers", False))
        root_span.set_attribute("workflow.engagement_score",
                                str(monitor_data.get("engagement_score", "?")))
        state["monitor_output"] = monitor_data
        checkpoint.save(run_id, state)

        if not monitor_data.get("should_generate_offers", False):
            reason = monitor_data.get("reason", "engagement or fatigue guard suppressed offers")
            emit("text_message", {"text": f"⛔ Offers suppressed: {reason}"})
            emit("run_finished", {"status": "suppressed"})
            state["workflow_status"] = "suppressed"
            checkpoint.save(run_id, state)
            root_span.set_attribute("workflow.status", "suppressed")
            return

        score = monitor_data.get("engagement_score", "?")
        emit("text_message", {
            "text": f"✅ Engagement score {score} — fatigue gate clear. Generating offers…"
        })

        # ── Step 2: Offer Generator ───────────────────────────────────────────────
        emit("tool_call_start", {"tool": "OfferGeneratorAgent"})

        generator_prompt = generator_def.build_offer_generation_prompt(
            fan_id=fan_id,
            game_id=game_id,
            section_id=state["preferred_section_id"],
            stadium_id=config.DEMO_STADIUM_ID,
            monitor_data=monitor_data,
            fan_name=state["fan_name"],
            fan_loyalty_tier=state["fan_loyalty_tier"],
            sport_context=state["sport_context"],
        )
        with tracer.start_as_current_span("workflow.offer_generator") as gen_span:
            generator_agent = generator_def.create_agent(credential)
            generator_response = await generator_agent.run(generator_prompt)
            generator_text = generator_response.text or ""
            gen_span.set_attribute("workflow.generator_response_length", len(generator_text))

        emit("tool_call_end", {"tool": "OfferGeneratorAgent", "output": generator_text[:200]})

        try:
            extracted = _extract_json(generator_text)
            log.info("OfferGenerator extracted JSON: %s", extracted[:500])
            generator_data = json.loads(extracted)
            offers: list[dict] = generator_data.get("offers", [])
            log.info("OfferGenerator parsed %d offers", len(offers))
        except Exception as exc:
            log.error("OfferGenerator JSON parse failed: %s | text: %s", exc, generator_text[:500])
            offers = []

        root_span.set_attribute("workflow.offers_generated", len(offers))

        if not offers:
            emit("text_message", {"text": "⛔ Offer generation failed — no offers returned by agent."})
            emit("run_finished", {"status": "suppressed"})
            state["workflow_status"] = "suppressed"
            checkpoint.save(run_id, state)
            root_span.set_attribute("workflow.status", "suppressed")
            return

        for offer in offers:
            if not offer.get("id"):
                offer["id"] = f"offer_{uuid.uuid4().hex[:8]}"

        # ── Guardrail validation ──────────────────────────────────────────────
        # Build game/fan state from monitor output. Fields available today:
        #   gameExcitementIndex, quarter, loyaltyTier, minutesSinceLastOffer,
        #   totalOffersThisGame, totalOfferValueThisGame.
        # Game-state signals requiring Eventhouse extension (isRedZone, down,
        # scoreDifferential, etc.) default to None → those guardrails fail-open
        # with a warning log until the engagement monitor is extended.
        game_state = {
            "gameExcitementIndex":      monitor_data.get("gameExcitementIndex") or monitor_data.get("engagement_score"),
            "quarter":                  monitor_data.get("quarter"),
            "isRedZone":                monitor_data.get("isRedZone"),
            "lastPlayType":             monitor_data.get("lastPlayType"),
            "timeSinceScore":           monitor_data.get("timeSinceScore") or monitor_data.get("timeSinceTD"),
            "down":                     monitor_data.get("down"),
            "scoreDifferential":        monitor_data.get("scoreDifferential"),
            "gameClockQ2LessThan2m30s": monitor_data.get("gameClockQ2LessThan2m30s"),
            "activeIncident":           monitor_data.get("activeIncident"),
        }
        fan_state = {
            "loyaltyTier":             monitor_data.get("loyalty_tier", "Bronze"),
            "minutesSinceLastOffer":   monitor_data.get("minutesSinceLastOffer"),
            "totalOffersThisGame":     monitor_data.get("totalOffersThisGame", 0),
            "totalOfferValueThisGame": monitor_data.get("totalOfferValueThisGame", 0.0),
        }

        guardrail_result = guardrail_validate_offers(offers, game_state, fan_state, sport=config.SPORTS_IQ_SPORT)
        offers = guardrail_result.clean_offers
        suppressed_offers = guardrail_result.suppressed_offers

        root_span.set_attribute("workflow.offers_guardrail_suppressed", len(suppressed_offers))
        for s_offer in suppressed_offers:
            emit("text_message", {
                "text": f"🛡️ Offer {s_offer['id']} suppressed by policy — {s_offer['guardrail_reason']}"
            })

        if not offers:
            emit("text_message", {"text": "⛔ All generated offers were suppressed by policy guardrails."})
            emit("run_finished", {"status": "suppressed"})
            state["workflow_status"] = "suppressed"
            state["suppressed_offers"] = suppressed_offers
            checkpoint.save(run_id, state)
            root_span.set_attribute("workflow.status", "suppressed")
            return

        state["offers"] = offers
        state["suppressed_offers"] = suppressed_offers
        state["pending_offers"] = [o["id"] for o in offers]
        state["workflow_status"] = "awaiting_approval"
        checkpoint.save(run_id, state)

        emit("state_snapshot", {"offers": offers, "workflow_status": "awaiting_approval"})
        emit("text_message", {
            "text": f"📋 {len(offers)} offers generated. Awaiting human review…"
        })
        for offer in offers:
            emit("approval_required", {"offer_id": offer["id"], "offer": offer})

        # ── HITL: wait for human decisions ───────────────────────────────────────
        decisions: dict[str, dict] = {}
        await_tasks = []
        for offer in offers:
            key = f"{run_id}:{offer['id']}"
            event = asyncio.Event()
            _approval_events[key] = event

            async def _wait_for(oid: str, ev: asyncio.Event) -> None:
                with tracer.start_as_current_span("workflow.hitl_wait") as hitl_span:
                    hitl_span.set_attribute("workflow.offer_id", oid)
                    await asyncio.wait_for(ev.wait(), timeout=600.0)
                    key_ = f"{run_id}:{oid}"
                    dec = _approval_decisions.get(key_, {})
                    decisions[oid] = dec
                    action = "approved" if dec.get("approved") else "rejected"
                    hitl_span.set_attribute("workflow.hitl_decision", action)
                    hitl_span.set_attribute("workflow.hitl_reason", dec.get("reason", ""))
                    emit("text_message", {
                        "text": f"{'✅' if dec.get('approved') else '❌'} {oid} {action}."
                    })

            await_tasks.append(_wait_for(offer["id"], event))

        await asyncio.gather(*await_tasks)

        state["approval_decisions"] = decisions
        checkpoint.save(run_id, state)

        approved_count = sum(1 for d in decisions.values() if d.get("approved"))
        root_span.set_attribute("workflow.offers_approved", approved_count)

        log.info(
            "HITL complete: %d approved, %d rejected out of %d offers",
            approved_count, len(offers) - approved_count, len(offers),
        )

        # ── Step 3: Offer Approver ────────────────────────────────────────────────
        emit("text_message", {"text": "⚡ Executing approval decisions…"})
        emit("tool_call_start", {"tool": "OfferApproverAgent"})

        # Pre-filter into approved / rejected lists so the LLM never has to reason
        # about which offers to act on — rejection context from one offer must NOT
        # bleed into another offer's approved action.
        approved_items = [
            {
                **offer,
                "fan_email": state["fan_email"],
                "fan_name": state["fan_name"],
                "loyalty_tier": state["fan_loyalty_tier"],
            }
            for offer in offers if decisions.get(offer["id"], {}).get("approved")
        ]
        rejected_items = [
            {
                "offer_id": offer["id"],
                "fan_id": fan_id,
                "game_id": game_id,
                "rejection_reason": decisions.get(offer["id"], {}).get("reason", "rejected"),
            }
            for offer in offers if not decisions.get(offer["id"], {}).get("approved")
        ]

        prompt_parts: list[str] = [
            "Process EVERY item below. Do not skip any. The decisions have already been made — just execute them.\n"
        ]
        if approved_items:
            prompt_parts.append(
                f"APPROVED — call send_fan_notification() for each of these {len(approved_items)} offer(s):\n"
                + json.dumps(approved_items, indent=2)
            )
        if rejected_items:
            prompt_parts.append(
                f"REJECTED — call log_rejection() for each of these {len(rejected_items)} offer(s):\n"
                + json.dumps(rejected_items, indent=2)
            )
        prompt_parts.append(
            f"After processing all offers, call post_teams_summary() for fan '{state['fan_name']}', "
            f"game '{game_id}'."
        )
        approver_prompt = "\n\n".join(prompt_parts)
        with tracer.start_as_current_span("workflow.offer_approver") as app_span:
            app_span.set_attribute("workflow.fan_email", state["fan_email"])
            app_span.set_attribute("workflow.approved_count", approved_count)
            approver_agent = approver_def.create_agent(credential)
            approver_response = await approver_agent.run(approver_prompt)
            approver_text = approver_response.text or ""
            app_span.set_attribute("workflow.approver_response_length", len(approver_text))

        emit("tool_call_end", {"tool": "OfferApproverAgent", "output": approver_text[:200]})

        state["approver_output"] = approver_text
        state["workflow_status"] = "completed"
        checkpoint.save(run_id, state)

        emit("state_snapshot", {
            "offers": offers,
            "decisions": decisions,
            "workflow_status": "completed",
        })
        emit("run_finished", {"status": "completed"})
        root_span.set_attribute("workflow.status", "completed")

        for offer in offers:
            key = f"{run_id}:{offer['id']}"
            _approval_events.pop(key, None)
            _approval_decisions.pop(key, None)


def get_state(run_id: str) -> dict | None:
    return checkpoint.load(run_id)


def _extract_json(text: str) -> str:
    """Extract the first JSON object or array from a text string."""
    start = min(
        (text.find(c) for c in ["{", "["] if c in text),
        default=0,
    )
    end = max(text.rfind("}"), text.rfind("]")) + 1
    return text[start:end] if end > start else text
