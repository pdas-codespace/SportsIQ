"""Graph-based workflow orchestrator using nodes and edges — EngagementMonitor → OfferGenerator → [HITL] → OfferApprover.

Flow:
  Node 1: EngagementMonitor -> Node 2: OfferGenerator -> Node 3: PolicyGuardrails -> Node 4: HITL -> Node 5: OfferApprover
  - Uses edge connections to define dependencies
  - Supports conditional branching (e.g., if suppressed, skip to end)
  - Maintains same interface: set_approval_decision(), start(), get_state()
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from azure.identity import DefaultAzureCredential
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from agents.engagement_monitor import agent_def as monitor_def
from agents.middleware.policy_guardrail import validate_offers as guardrail_validate_offers
from agents.offer_approver import agent_def as approver_def
from agents.offer_approver import checkpoint
from agents.offer_generator import agent_def as generator_def
from agents.shared import config, telemetry

log = logging.getLogger(__name__)
_tracer = telemetry.get_tracer()
_LATENCY_BUDGET_MS = 6000
_APPLICATION_ID = os.getenv("SPORTS_IQ_APPLICATION_ID", "sports-iq")
_DEPLOYMENT_ENVIRONMENT = (
    os.getenv("SPORTS_IQ_ENVIRONMENT")
    or os.getenv("AZURE_ENV_NAME")
    or os.getenv("ENVIRONMENT")
    or "development"
)
_BUILD_ID = (
    os.getenv("SPORTS_IQ_BUILD_ID")
    or os.getenv("GITHUB_SHA")
    or os.getenv("BUILD_BUILDID")
    or "local"
)
_DEPLOYMENT_ID = os.getenv("SPORTS_IQ_DEPLOYMENT_ID", _BUILD_ID)
_TENANT_ID = os.getenv("SPORTS_IQ_TENANT_ID", "sports-iq")
_DEFAULT_AGENT_NAME = "workflow-orchestrator"

_NODE_AGENT_NAMES = {
    "engagement_monitor": "engagement-monitor",
    "offer_generator": "offer-generator",
    "policy_guardrails": "policy-guardrails",
    "hitl_approval": "hitl-approval",
    "offer_approver": "offer-approver",
    "terminal_success": "workflow-terminal",
    "terminal_suppressed": "workflow-terminal",
}

# ── HITL state ────────────────────────────────────────────────────────────────
_approval_events: dict[str, asyncio.Event] = {}
_approval_decisions: dict[str, dict[str, Any]] = {}


def _set_span_attribute(span: trace.Span, key: str, value: Any) -> None:
    if value is None:
        return
    span.set_attribute(key, value)


def _set_span_context(
    span: trace.Span,
    ctx: dict[str, Any],
    agent_name: str | None = None,
) -> None:
    session_id = ctx.get("session_id") or ctx.get("run_id")
    conversation_id = ctx.get("conversation_id") or session_id
    user_id = ctx.get("user_id") or ctx.get("fan_id")
    tenant_id = ctx.get("tenant_id") or _TENANT_ID

    span.set_attribute("service.name", _APPLICATION_ID)
    span.set_attribute("service.version", _BUILD_ID)
    span.set_attribute("deployment.environment.name", _DEPLOYMENT_ENVIRONMENT)
    span.set_attribute("sportsiq.application_id", _APPLICATION_ID)
    span.set_attribute("sportsiq.deployment_id", _DEPLOYMENT_ID)
    span.set_attribute("sportsiq.environment", _DEPLOYMENT_ENVIRONMENT)
    span.set_attribute("sportsiq.agent_name", agent_name or ctx.get("agent_name") or _DEFAULT_AGENT_NAME)

    _set_span_attribute(span, "session.id", session_id)
    _set_span_attribute(span, "conversation.id", conversation_id)
    _set_span_attribute(span, "sportsiq.session_id", session_id)
    _set_span_attribute(span, "sportsiq.conversation_id", conversation_id)
    _set_span_attribute(span, "user.id", user_id)
    _set_span_attribute(span, "enduser.id", user_id)
    _set_span_attribute(span, "tenant.id", tenant_id)
    _set_span_attribute(span, "sportsiq.tenant_id", tenant_id)
    _set_span_attribute(span, "sportsiq.workflow.run_id", ctx.get("run_id"))
    _set_span_attribute(span, "sportsiq.fan_id", ctx.get("fan_id"))
    _set_span_attribute(span, "sportsiq.game_id", ctx.get("game_id"))
    _set_span_attribute(span, "sportsiq.latency_budget_ms", _LATENCY_BUDGET_MS)


def _set_span_success(span: trace.Span) -> None:
    span.set_status(Status(StatusCode.OK))


def _set_span_error(span: trace.Span, exc: Exception) -> None:
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR, str(exc)))


def _emit(ctx: dict[str, Any], event_type: str, payload: dict[str, Any]) -> None:
    emitter = ctx.get("emit")
    if callable(emitter):
        emitter(event_type, payload)


def _save_state(ctx: dict[str, Any], updates: dict[str, Any]) -> None:
    state = ctx.get("state")
    run_id = ctx.get("run_id")
    if not isinstance(state, dict) or not isinstance(run_id, str):
        return

    state.update(updates)
    checkpoint.save(run_id, state)


def set_approval_decision(run_id: str, offer_id: str, approved: bool, reason: str = "") -> None:
    """Called by server endpoints when a human decision is submitted."""
    key = f"{run_id}:{offer_id}"
    _approval_decisions[key] = {"approved": approved, "reason": reason}
    event = _approval_events.get(key)
    if event:
        event.set()
    else:
        log.warning("set_approval_decision: no pending event for key=%s", key)


# ── Node and Edge Definitions ─────────────────────────────────────────────────

@dataclass
class Node:
    """A node represents a single workflow step."""
    name: str
    node_type: str  # "step", "decision", "hitl", "terminal"
    execute_fn: Callable[[dict[str, Any]], Any] | None = None
    inputs: list[str] = field(default_factory=list)  # input keys from context
    outputs: dict[str, str] = field(default_factory=dict)  # {output_key: input_key}


@dataclass
class Edge:
    """An edge connects two nodes with optional conditions."""
    source: str  # source node name
    target: str  # target node name
    condition: Callable[[dict[str, Any]], bool] | None = None  # if None, always traverse


class WorkflowGraph:
    """Graph-based workflow executor with nodes and edges."""

    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.context: dict[str, Any] = {}

    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        self.nodes[node.name] = node

    def add_edge(
        self,
        source: str,
        target: str,
        condition: Callable[[dict[str, Any]], bool] | None = None,
    ) -> None:
        """Add an edge between two nodes."""
        self.edges.append(Edge(source, target, condition))

    async def execute(self, start_node: str) -> dict[str, Any]:
        """Execute the workflow starting from start_node."""
        current_node_name = start_node
        visited = set()

        while current_node_name:
            if current_node_name in visited:
                log.warning("Cycle detected at node %s; stopping", current_node_name)
                break

            visited.add(current_node_name)
            node = self.nodes.get(current_node_name)
            if not node:
                log.error("Node %s not found", current_node_name)
                break
            log.info("Executing node: %s", node.name)

            with _tracer.start_as_current_span(f"sportsiq.workflow.node.{node.name}") as span:
                _set_span_context(span, self.context, _NODE_AGENT_NAMES.get(node.name))
                span.set_attribute("sportsiq.workflow.node_name", node.name)
                span.set_attribute("sportsiq.workflow.node_type", node.node_type)

                if node.node_type == "terminal":
                    self.context["terminal_node"] = node.name
                    span.set_attribute("sportsiq.workflow.terminal_node", node.name)
                    _set_span_success(span)
                    break

                # Execute the node
                if node.execute_fn:
                    try:
                        result = await node.execute_fn(self.context)
                        if result is not None:
                            self.context.update(result if isinstance(result, dict) else {node.name: result})
                    except Exception as exc:
                        log.exception("Error executing node %s: %s", node.name, exc)
                        self.context[f"{node.name}_error"] = str(exc)
                        _set_span_error(span, exc)
                        raise

                # Find next node
                next_node = self._find_next_node(node.name)
                if not next_node:
                    span.set_attribute("sportsiq.workflow.next_node", "")
                    _set_span_success(span)
                    break

                span.set_attribute("sportsiq.workflow.next_node", next_node)
                _set_span_success(span)
                current_node_name = next_node

        return self.context

    def _find_next_node(self, source_node: str) -> str | None:
        """Find the next node based on edges and conditions."""
        for edge in self.edges:
            if edge.source == source_node:
                # Check condition
                if edge.condition is None or edge.condition(self.context):
                    return edge.target
        return None


def _extract_json(text: str) -> str:
    start = min((text.find(c) for c in ["{", "["] if c in text), default=0)
    end = max(text.rfind("}"), text.rfind("]")) + 1
    return text[start:end] if end > start else text


# ── Node Execution Functions ───────────────────────────────────────────────────

async def _execute_engagement_monitor(ctx: dict[str, Any]) -> dict[str, Any]:
    """Run engagement monitor agent."""
    fan_id = ctx["fan_id"]
    game_id = ctx["game_id"]
    span = trace.get_current_span()
    _set_span_context(span, ctx, "engagement-monitor")

    _emit(ctx, "text_message", {"text": "🔍 Checking engagement score and offer fatigue gate…"})
    _emit(ctx, "tool_call_start", {"tool": "EngagementMonitorAgent"})

    credential = DefaultAzureCredential()
    agent = monitor_def.create_agent(credential)
    prompt = (
        f"Check engagement for fan_id={fan_id}, game_id={game_id}. "
        "Should we generate offers right now?"
    )
    response = await agent.run(prompt)
    text = response.text or ""
    span.set_attribute("sportsiq.workflow.response_length", len(text))
    try:
        monitor_data = json.loads(_extract_json(text))
    except Exception as exc:
        span.record_exception(exc)
        span.set_attribute("sportsiq.workflow.parse_error", True)
        monitor_data = {"should_generate_offers": False, "reason": text}

    _emit(ctx, "tool_call_end", {"tool": "EngagementMonitorAgent", "output": text[:200]})
    _save_state(ctx, {"monitor_output": monitor_data})

    span.set_attribute(
        "sportsiq.workflow.should_generate_offers",
        bool(monitor_data.get("should_generate_offers", False)),
    )
    _set_span_attribute(span, "sportsiq.engagement_score", monitor_data.get("engagement_score"))

    if not monitor_data.get("should_generate_offers", False):
        reason = monitor_data.get("reason", "engagement or fatigue guard suppressed offers")
        _emit(ctx, "text_message", {"text": f"⛔ Offers suppressed: {reason}"})
    else:
        score = monitor_data.get("engagement_score", "?")
        _emit(ctx, "text_message", {
            "text": f"✅ Engagement score {score} — fatigue gate clear. Generating offers…"
        })

    return {"monitor_data": monitor_data}


async def _execute_offer_generator(ctx: dict[str, Any]) -> dict[str, Any]:
    """Run offer generator agent."""
    fan_id = ctx["fan_id"]
    game_id = ctx["game_id"]
    monitor_data = ctx["monitor_data"]
    section_id = ctx.get("preferred_section_id") or config.DEMO_SECTION_ID
    span = trace.get_current_span()
    _set_span_context(span, ctx, "offer-generator")

    _emit(ctx, "tool_call_start", {"tool": "OfferGeneratorAgent"})

    credential = DefaultAzureCredential()
    agent = generator_def.create_agent(credential)
    prompt = generator_def.build_offer_generation_prompt(
        fan_id=fan_id,
        game_id=game_id,
        section_id=section_id,
        stadium_id=config.DEMO_STADIUM_ID,
        monitor_data=monitor_data,
        fan_name=ctx.get("fan_name", ""),
        fan_loyalty_tier=ctx.get("fan_loyalty_tier", ""),
        sport_context=ctx.get("sport_context"),
    )
    response = await agent.run(prompt)
    text = response.text or ""
    span.set_attribute("sportsiq.workflow.response_length", len(text))

    _emit(ctx, "tool_call_end", {"tool": "OfferGeneratorAgent", "output": text[:200]})

    try:
        payload = json.loads(_extract_json(text))
        offers = payload.get("offers", [])
    except Exception as exc:
        span.record_exception(exc)
        span.set_attribute("sportsiq.workflow.parse_error", True)
        offers = []

    for offer in offers:
        if not offer.get("id"):
            offer["id"] = f"offer_{uuid.uuid4().hex[:8]}"
        span.add_event(
            "offer.proposed",
            {
                "sportsiq.offer_id": offer["id"],
                "sportsiq.offer_category": str(offer.get("category", "")),
            },
        )

    span.set_attribute("sportsiq.workflow.offers_generated", len(offers))

    if not offers:
        _emit(ctx, "text_message", {"text": "⛔ Offer generation failed — no offers returned by agent."})

    return {"offers": offers}


async def _execute_policy_guardrails(ctx: dict[str, Any]) -> dict[str, Any]:
    """Apply policy guardrails to offers."""
    offers = ctx["offers"]
    monitor_data = ctx["monitor_data"]
    span = trace.get_current_span()
    _set_span_context(span, ctx)

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
    span.set_attribute("sportsiq.guardrail.tripped", len(result.suppressed_offers) > 0)
    span.set_attribute("sportsiq.workflow.offers_clean", len(result.clean_offers))
    span.set_attribute("sportsiq.workflow.offers_guardrail_suppressed", len(result.suppressed_offers))

    for suppressed_offer in result.suppressed_offers:
        span.add_event(
            "guardrail.evaluated",
            {
                "sportsiq.guardrail.tripped": True,
                "sportsiq.offer_id": str(suppressed_offer.get("id", "")),
                "sportsiq.guardrail.reason": str(suppressed_offer.get("guardrail_reason", "")),
            },
        )
        _emit(ctx, "text_message", {
            "text": (
                f"🛡️ Offer {suppressed_offer['id']} suppressed by policy — "
                f"{suppressed_offer['guardrail_reason']}"
            )
        })

    if not result.clean_offers:
        _emit(ctx, "text_message", {"text": "⛔ All generated offers were suppressed by policy guardrails."})

    return {"clean_offers": result.clean_offers, "suppressed_offers": result.suppressed_offers}


async def _execute_hitl_approval(ctx: dict[str, Any]) -> dict[str, Any]:
    """Wait for HITL approval for each offer."""
    run_id = ctx["run_id"]
    offers = ctx["clean_offers"]
    span = trace.get_current_span()
    _set_span_context(span, ctx)
    span.set_attribute("sportsiq.workflow.pending_approvals", len(offers))

    _save_state(ctx, {
        "offers": offers,
        "suppressed_offers": ctx.get("suppressed_offers", []),
        "pending_offers": [offer["id"] for offer in offers],
        "workflow_status": "awaiting_approval",
    })

    _emit(ctx, "state_snapshot", {"offers": offers, "workflow_status": "awaiting_approval"})
    _emit(ctx, "text_message", {
        "text": f"📋 {len(offers)} offers generated. Awaiting human review…"
    })

    waiters: list[tuple[str, asyncio.Event]] = []
    for offer in offers:
        key = f"{run_id}:{offer['id']}"
        event = asyncio.Event()
        _approval_events[key] = event
        if key in _approval_decisions:
            event.set()
        waiters.append((offer["id"], event))
        span.add_event("approval.requested", {"sportsiq.offer_id": offer["id"]})
        _emit(ctx, "approval_required", {"offer_id": offer["id"], "offer": offer})

    async def _wait_for(offer_id: str, event: asyncio.Event) -> tuple[str, dict[str, Any]]:
        with _tracer.start_as_current_span("sportsiq.workflow.hitl_wait") as hitl_span:
            _set_span_context(hitl_span, ctx)
            hitl_span.set_attribute("sportsiq.offer_id", offer_id)
            try:
                await asyncio.wait_for(event.wait(), timeout=600.0)
                key = f"{run_id}:{offer_id}"
                decision = _approval_decisions.get(key, {"approved": False, "reason": "timeout"})
                action = "approved" if decision.get("approved") else "rejected"
                hitl_span.set_attribute("sportsiq.workflow.hitl_decision", action)
                _emit(ctx, "text_message", {
                    "text": f"{'✅' if decision.get('approved') else '❌'} {offer_id} {action}."
                })
                _set_span_success(hitl_span)
                return offer_id, decision
            except Exception as exc:
                _set_span_error(hitl_span, exc)
                raise

    results = await asyncio.gather(*(_wait_for(offer_id, event) for offer_id, event in waiters))
    decisions = {offer_id: decision for offer_id, decision in results}
    approved_count = sum(1 for decision in decisions.values() if decision.get("approved"))
    span.set_attribute("sportsiq.workflow.offers_approved", approved_count)
    _save_state(ctx, {"approval_decisions": decisions})

    return {"decisions": decisions}


async def _execute_offer_approver(ctx: dict[str, Any]) -> dict[str, Any]:
    """Run offer approver agent."""
    fan_id = ctx["fan_id"]
    game_id = ctx["game_id"]
    fan_name = ctx["fan_name"]
    fan_loyalty_tier = ctx["fan_loyalty_tier"]
    fan_email = ctx["fan_email"]
    offers = ctx["clean_offers"]
    decisions = ctx["decisions"]
    span = trace.get_current_span()
    _set_span_context(span, ctx, "offer-approver")

    _emit(ctx, "text_message", {"text": "⚡ Executing approval decisions…"})
    _emit(ctx, "tool_call_start", {"tool": "OfferApproverAgent"})

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
    span.set_attribute("sportsiq.workflow.offers_approved", len(approved_items))
    span.set_attribute("sportsiq.workflow.offers_rejected", len(rejected_items))

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
    text = response.text or ""
    span.set_attribute("sportsiq.workflow.response_length", len(text))
    _emit(ctx, "tool_call_end", {"tool": "OfferApproverAgent", "output": text[:200]})
    _save_state(ctx, {"approver_output": text})
    return {"approver_output": text}


# ── Workflow Assembly ──────────────────────────────────────────────────────────

def _build_workflow_graph() -> WorkflowGraph:
    """Construct the nodes-and-edges workflow graph."""
    graph = WorkflowGraph()

    # Define nodes
    graph.add_node(Node(
        name="engagement_monitor",
        node_type="step",
        execute_fn=_execute_engagement_monitor,
    ))
    graph.add_node(Node(
        name="offer_generator",
        node_type="step",
        execute_fn=_execute_offer_generator,
    ))
    graph.add_node(Node(
        name="policy_guardrails",
        node_type="step",
        execute_fn=_execute_policy_guardrails,
    ))
    graph.add_node(Node(
        name="hitl_approval",
        node_type="hitl",
        execute_fn=_execute_hitl_approval,
    ))
    graph.add_node(Node(
        name="offer_approver",
        node_type="step",
        execute_fn=_execute_offer_approver,
    ))
    graph.add_node(Node(
        name="terminal_success",
        node_type="terminal",
    ))
    graph.add_node(Node(
        name="terminal_suppressed",
        node_type="terminal",
    ))

    # Define edges with conditions
    # engagement_monitor -> offer_generator (if should_generate_offers)
    graph.add_edge(
        "engagement_monitor",
        "offer_generator",
        condition=lambda ctx: ctx.get("monitor_data", {}).get("should_generate_offers", False),
    )
    # engagement_monitor -> terminal_suppressed (if should_generate_offers is False)
    graph.add_edge(
        "engagement_monitor",
        "terminal_suppressed",
        condition=lambda ctx: not ctx.get("monitor_data", {}).get("should_generate_offers", True),
    )

    # offer_generator -> policy_guardrails (if offers exist)
    graph.add_edge(
        "offer_generator",
        "policy_guardrails",
        condition=lambda ctx: len(ctx.get("offers", [])) > 0,
    )
    # offer_generator -> terminal_suppressed (if no offers)
    graph.add_edge(
        "offer_generator",
        "terminal_suppressed",
        condition=lambda ctx: len(ctx.get("offers", [])) == 0,
    )

    # policy_guardrails -> hitl_approval (if clean_offers exist)
    graph.add_edge(
        "policy_guardrails",
        "hitl_approval",
        condition=lambda ctx: len(ctx.get("clean_offers", [])) > 0,
    )
    # policy_guardrails -> terminal_suppressed (if all offers suppressed)
    graph.add_edge(
        "policy_guardrails",
        "terminal_suppressed",
        condition=lambda ctx: len(ctx.get("clean_offers", [])) == 0,
    )

    # hitl_approval -> offer_approver (always)
    graph.add_edge("hitl_approval", "offer_approver")

    # offer_approver -> terminal_success (always)
    graph.add_edge("offer_approver", "terminal_success")

    return graph


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
    """Run the graph-based workflow and bridge HITL to existing approval endpoints."""

    def emit(event_type: str, payload: dict[str, Any]) -> None:
        try:
            event_emitter(event_type, {"run_id": run_id, **payload})
        except Exception as exc:
            log.error("event_emitter error: %s", exc)

    state: dict[str, Any] = {
        "run_id": run_id,
        "fan_id": fan_id,
        "game_id": game_id,
        "session_id": run_id,
        "conversation_id": run_id,
        "user_id": fan_id,
        "tenant_id": _TENANT_ID,
        "fan_name": fan_name or config.DEMO_FAN_NAME,
        "fan_loyalty_tier": fan_loyalty_tier or "Gold",
        "fan_email": fan_email or config.DEMO_FAN_EMAIL,
        "preferred_section_id": preferred_section_id or config.DEMO_SECTION_ID,
        "sport_context": sport_context or config.default_sport_context(),
        "workflow_status": "started",
    }

    with _tracer.start_as_current_span("sportsiq.workflow.graph.run") as root_span:
        _set_span_context(root_span, state)
        root_span.set_attribute("sportsiq.workflow.kind", "nodes_edges")

        checkpoint.save(run_id, state)

        emit("run_started", {"fan_id": fan_id, "game_id": game_id})
        emit("text_message", {"text": "Starting graph-based Sports-IQ workflow..."})

        try:
            # Build and execute the workflow graph
            graph = _build_workflow_graph()
            graph.context = {
                "run_id": run_id,
                "fan_id": fan_id,
                "game_id": game_id,
                "session_id": state["session_id"],
                "conversation_id": state["conversation_id"],
                "user_id": state["user_id"],
                "tenant_id": state["tenant_id"],
                "fan_name": state["fan_name"],
                "fan_loyalty_tier": state["fan_loyalty_tier"],
                "fan_email": state["fan_email"],
                "preferred_section_id": state["preferred_section_id"],
                "sport_context": state["sport_context"],
                "emit": emit,
                "state": state,
            }

            final_context = await graph.execute("engagement_monitor")

            # Determine final status
            terminal_node = final_context.get("terminal_node")

            if terminal_node is None:
                # Fallback: check if we hit a terminal
                if "approver_output" in final_context:
                    terminal_node = "terminal_success"
                elif final_context.get("monitor_data", {}).get("should_generate_offers") is False:
                    terminal_node = "terminal_suppressed"

            workflow_status = "completed" if terminal_node == "terminal_success" else "suppressed"
            state["workflow_status"] = workflow_status
            state["offers"] = final_context.get("clean_offers", [])
            state["approval_decisions"] = final_context.get("decisions", {})
            state["suppressed_offers"] = final_context.get("suppressed_offers", [])

            root_span.set_attribute("sportsiq.workflow.status", workflow_status)
            _set_span_attribute(root_span, "sportsiq.workflow.terminal_node", terminal_node)
            root_span.set_attribute("sportsiq.workflow.offers_clean", len(state["offers"]))
            root_span.set_attribute("sportsiq.workflow.offers_guardrail_suppressed", len(state["suppressed_offers"]))
            root_span.set_attribute(
                "sportsiq.workflow.offers_approved",
                sum(1 for decision in state["approval_decisions"].values() if decision.get("approved")),
            )

            checkpoint.save(run_id, state)

            if workflow_status == "completed":
                emit("state_snapshot", {
                    "run_id": run_id,
                    "workflow_status": workflow_status,
                    "offers": state["offers"],
                    "decisions": state["approval_decisions"],
                })
                emit("run_finished", {"status": "completed"})
            else:
                emit("run_finished", {"status": "suppressed"})

            _set_span_success(root_span)

        except Exception as exc:
            log.exception("Graph workflow failed for run_id=%s", run_id)
            state["workflow_status"] = "failed"
            state["error"] = str(exc)
            checkpoint.save(run_id, state)
            root_span.set_attribute("sportsiq.workflow.status", "failed")
            _set_span_error(root_span, exc)
            emit("run_error", {"error": str(exc)})
        finally:
            keys = [key for key in list(_approval_events.keys()) if key.startswith(f"{run_id}:")]
            for key in keys:
                _approval_events.pop(key, None)
                _approval_decisions.pop(key, None)
