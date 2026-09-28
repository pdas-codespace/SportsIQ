"""
FastAPI server with AG-UI compatible SSE streaming.

Endpoints:
  POST /api/run              — start a new workflow run
  GET  /api/run/{run_id}/stream  — SSE stream of AG-UI events
  POST /api/run/{run_id}/tool-result  — human approval/rejection decision
  GET  /api/run/{run_id}/state — get current workflow state

All concurrency is pure asyncio (no threading). The workflow runs as an
asyncio task in the same event loop as FastAPI — this is required for
asyncio.Event HITL to work correctly.
"""
from __future__ import annotations

# ── Load .env FIRST so all os.getenv() / os.environ calls below see the values ──
# python-dotenv handles quoted values and multi-segment = signs (connection strings)
# correctly; the PowerShell pre-loading approach can corrupt base64-padded keys.
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass  # python-dotenv not installed; rely on shell env vars

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

#import agents.workflow as workflow
import agents.workflow_nodes_edges as workflow
from agents.shared import config, telemetry
from agents.offer_approver import checkpoint

# ── Telemetry: configure OTEL + App Insights before anything else ─────────────
telemetry.setup()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Sports-IQ Agent Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.on_event("startup")
async def validate_runtime_configuration() -> None:
    missing = config.missing_runtime_settings()
    if missing:
        raise RuntimeError(
            "Missing required runtime settings: " + ", ".join(sorted(missing))
        )


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# Per-run asyncio queues: run_id → asyncio.Queue[dict]
_event_queues: dict[str, asyncio.Queue] = {}


# ── Pydantic models ───────────────────────────────────────────────────────────

class StartRunRequest(BaseModel):
    fan_id: str = config.DEMO_FAN_ID
    game_id: str = config.DEMO_GAME_ID
    fan_name: str = config.DEMO_FAN_NAME
    fan_loyalty_tier: str = "Gold"
    fan_email: str = ""  # demo override; falls back to config.DEMO_FAN_EMAIL when empty
    preferred_section_id: str = config.DEMO_SECTION_ID
    sport_context: dict[str, Any] = Field(default_factory=config.default_sport_context)


class ToolResultRequest(BaseModel):
    offer_id: str
    approved: bool
    reason: str = ""


class GameEventRequest(BaseModel):
    break_type: str  # tv_timeout | commercial | halftime | two_minute_warning
    game_id: str = config.DEMO_GAME_ID


class ChatRequest(BaseModel):
    message: str
    previous_response_id: str | None = None


class RedeemOfferRequest(BaseModel):
    fan_id: str
    fan_name: str = ""
    game_id: str
    promo_id: str
    offer_title: str
    offer_category: str   # merchandise | food_beverage
    offer_type: str        # percentage_discount | fixed_amount
    offer_value: float     # e.g. 20.0 for "20% off" or 5.0 for "$5 off"
    unit_price: float = 89.0  # original price before discount
    section_id: str = config.DEMO_SECTION_ID


_TIER_THRESHOLDS = {"Platinum": 0.65, "Gold": 0.55, "Silver": 0.45, "Bronze": 0.45}
_BREAK_LABELS = {
    "tv_timeout": "TV Timeout",
    "commercial": "Commercial Break",
    "halftime": "Halftime",
    "two_minute_warning": "2-Minute Warning",
}


# ── AG-UI event helpers ───────────────────────────────────────────────────────

def _make_event(event_type: str, data: dict) -> dict:
    return {
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **data,
    }


def _sse_line(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


def _build_emitter(run_id: str, q: asyncio.Queue):
    """Returns a callable emitter that puts AG-UI events onto the asyncio queue."""

    def emit(event_type: str, payload: dict) -> None:
        event: dict | None = None
        if event_type == "run_started":
            event = _make_event("RUN_STARTED", payload)
        elif event_type == "text_message":
            msg_id = str(uuid.uuid4())
            q.put_nowait(_make_event("TEXT_MESSAGE_START", {"message_id": msg_id}))
            q.put_nowait(_make_event("TEXT_MESSAGE_CONTENT", {"message_id": msg_id, "delta": payload.get("text", "")}))
            event = _make_event("TEXT_MESSAGE_END", {"message_id": msg_id})
        elif event_type == "tool_call_start":
            event = _make_event("TOOL_CALL_START", {
                "tool_call_id": str(uuid.uuid4()),
                "tool_name": payload.get("tool", ""),
            })
        elif event_type == "tool_call_end":
            event = _make_event("TOOL_CALL_END", payload)
        elif event_type == "state_snapshot":
            event = _make_event("STATE_SNAPSHOT", {"snapshot": payload})
        elif event_type == "approval_required":
            # AG-UI client tool call — frontend renders approval card and POSTs tool-result
            event = _make_event("TOOL_CALL_START", {
                "tool_call_id": payload["offer_id"],
                "tool_name": "request_approval",
                "tool_call_type": "client",
                "args": {
                    "run_id": run_id,
                    "offer_id": payload["offer_id"],
                    "offer": payload["offer"],
                },
            })
        elif event_type == "run_finished":
            event = _make_event("RUN_FINISHED", payload)
        elif event_type == "run_error":
            event = _make_event("RUN_ERROR", payload)

        if event:
            q.put_nowait(event)

    return emit


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/fans")
async def get_fans(mode: str, value: str = "", sections: str = ""):
    """
    Search fans with offer-fatigue status via direct Lakehouse SQL.
    mode=tier    &value=Gold
    mode=section &sections=S101,S102,S103   (comma-separated)
    Returns {"fans": [...]} where each fan has offerFatigued flag.
    """
    from agents.shared import lakehouse_client

    try:
        if mode == "tier":
            if not value:
                raise HTTPException(400, "value required for mode=tier")
            fans = await asyncio.to_thread(
                lakehouse_client.get_fans_by_tier,
                value, config.LAKEHOUSE_SQL_ENDPOINT, config.LAKEHOUSE_DB, config.LAKEHOUSE_SCHEMA,
            )
        elif mode == "section":
            if not sections:
                raise HTTPException(400, "sections required for mode=section")
            section_list = [s.strip() for s in sections.split(",") if s.strip()]
            fans = await asyncio.to_thread(
                lakehouse_client.get_fans_by_sections,
                section_list, config.LAKEHOUSE_SQL_ENDPOINT, config.LAKEHOUSE_DB, config.LAKEHOUSE_SCHEMA,
            )
        else:
            raise HTTPException(400, f"Unknown mode '{mode}'. Use 'tier' or 'section'.")
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Fan search failed (mode=%s)", mode)
        raise HTTPException(502, f"Lakehouse query error: {exc}") from exc

    return {"fans": fans}


@app.get("/api/fans/{fan_id}")
async def get_fan_detail(fan_id: str):
    """Return full fan profile + recent offers for the fan detail panel."""
    from agents.shared import lakehouse_client
    try:
        detail = await asyncio.to_thread(
            lakehouse_client.get_fan_detail,
            fan_id, config.LAKEHOUSE_SQL_ENDPOINT, config.LAKEHOUSE_DB, config.LAKEHOUSE_SCHEMA,
        )
    except Exception as exc:
        log.exception("Fan detail lookup failed for %s", fan_id)
        raise HTTPException(502, f"Lakehouse error: {exc}") from exc
    if detail is None:
        raise HTTPException(404, f"Fan '{fan_id}' not found")
    return detail


@app.post("/api/game-event")
async def simulate_game_event(req: GameEventRequest):
    """Simulate a game break event, scan Eventhouse for disengaged fans, and return them ranked.

    This is the entry point for the event-driven UX flow:
      1. Operator simulates a break (TV timeout / commercial / halftime / 2-min warning)
      2. System scans Eventhouse for every fan in the game whose latest engagement score
         is below their loyalty-tier threshold
      3. Returns a ranked list of triggered fans (most disengaged first)
    """
    from agents.shared import eventhouse_client, lakehouse_client

    engagement_rows = await asyncio.to_thread(
        eventhouse_client.scan_disengaged_fans,
        req.game_id, config.EVENTHOUSE_URI, config.EVENTHOUSE_DB,
    )

    if not engagement_rows:
        return {
            "break_type": req.break_type,
            "break_label": _BREAK_LABELS.get(req.break_type, req.break_type),
            "game_id": req.game_id,
            "triggered_fans": [],
        }

    fan_ids = [r["fanId"] for r in engagement_rows]
    profiles = await asyncio.to_thread(
        lakehouse_client.get_fan_profiles_for_ids,
        fan_ids, config.LAKEHOUSE_SQL_ENDPOINT, config.LAKEHOUSE_DB, config.LAKEHOUSE_SCHEMA,
    )
    profile_map = {p["fanId"]: p for p in profiles}

    triggered = []
    for e in engagement_rows:
        fan_id = e["fanId"]
        profile = profile_map.get(fan_id)
        if not profile:
            continue
        tier = profile.get("loyaltyTier", "Bronze")
        threshold = _TIER_THRESHOLDS.get(tier, 0.45)
        score = round(float(e.get("engagementScore", 1.0)), 2)
        if score < threshold:
            base_score = float(profile.get("baseEngagementScore") or 0.5)
            triggered.append({
                "fanId": fan_id,
                "fanName": profile.get("fanName") or fan_id,
                "loyaltyTier": tier,
                "preferredSectionId": profile.get("preferredSectionId") or e.get("sectionId") or "",
                "baseEngagementScore": round(base_score, 2),
                "currentEngagementScore": score,
                "engagementDropAmount": round(max(0.0, base_score - score), 2),
                "triggerThreshold": threshold,
                "triggerReason": f"Score {score:.2f} — below {tier} threshold {threshold}",
                "quarter": e.get("quarter"),
                "gameMinute": e.get("gameMinute"),
                "churnRiskScore": round(float(profile.get("churnRiskScore") or 0), 2),
                "lastOfferDaysAgo": profile.get("lastOfferDaysAgo", -1),
                "offerFatigued": profile.get("offerFatigued", False),
            })

    triggered.sort(key=lambda x: x["currentEngagementScore"])

    return {
        "break_type": req.break_type,
        "break_label": _BREAK_LABELS.get(req.break_type, req.break_type),
        "game_id": req.game_id,
        "triggered_fans": triggered,
    }


@app.post("/api/run")
async def start_run(req: StartRunRequest):
    """Create a run_id and return it. Connect to /stream to start the workflow."""
    run_id = checkpoint.new_run_id()
    checkpoint.save(run_id, {
        "run_id": run_id,
        "fan_id": req.fan_id,
        "game_id": req.game_id,
        "fan_name": req.fan_name,
        "fan_loyalty_tier": req.fan_loyalty_tier,
        "fan_email": req.fan_email or config.DEMO_FAN_EMAIL,
        "preferred_section_id": req.preferred_section_id,
        "sport_context": req.sport_context,
        "workflow_status": "starting",
    })
    return {"run_id": run_id}


@app.get("/api/run/{run_id}/stream")
async def stream_run(run_id: str):
    """
    SSE endpoint. Starts the workflow as an asyncio task and streams AG-UI events.
    Connect here after receiving run_id from POST /api/run.
    """
    state = checkpoint.load(run_id)
    if not state:
        raise HTTPException(404, f"Run {run_id} not found")

    # If the workflow already completed, replay the final state without re-running.
    if state.get("workflow_status") == "completed":
        async def _replay() -> AsyncGenerator[str, None]:
            yield _sse_line({"type": "CONNECTED", "run_id": run_id})
            yield _sse_line(_make_event("STATE_SNAPSHOT", {
                "snapshot": {
                    "run_id": run_id,
                    "workflow_status": "completed",
                    "offers": state.get("offers", []),
                    "decisions": state.get("approval_decisions", {}),
                },
            }))
            yield _sse_line(_make_event("RUN_FINISHED", {"status": "completed"}))
        return StreamingResponse(
            _replay(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    q: asyncio.Queue = asyncio.Queue()
    _event_queues[run_id] = q

    emitter = _build_emitter(run_id, q)

    async def run_and_catch() -> None:
        try:
            await workflow.start(
                run_id=run_id,
                fan_id=state["fan_id"],
                game_id=state["game_id"],
                event_emitter=emitter,
                fan_name=state.get("fan_name"),
                fan_loyalty_tier=state.get("fan_loyalty_tier"),
                fan_email=state.get("fan_email"),
                preferred_section_id=state.get("preferred_section_id"),
                sport_context=state.get("sport_context"),
            )
        except Exception as exc:
            log.exception("Workflow error for run %s", run_id)
            emitter("run_error", {"run_id": run_id, "error": str(exc)})

    asyncio.create_task(run_and_catch())

    async def event_generator() -> AsyncGenerator[str, None]:
        yield _sse_line({"type": "CONNECTED", "run_id": run_id})
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30.0)
                yield _sse_line(event)
                if event.get("type") in ("RUN_FINISHED", "RUN_ERROR"):
                    break
            except asyncio.TimeoutError:
                yield ": ping\n\n"  # SSE keep-alive

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.post("/api/run/{run_id}/tool-result")
async def handle_tool_result(run_id: str, req: ToolResultRequest):
    """
    Receive the human approval/rejection decision (AG-UI client tool result).
    Directly calls workflow.set_approval_decision() — which sets an asyncio.Event
    in the same event loop, unblocking the waiting workflow task.
    """
    state = checkpoint.load(run_id)
    if not state:
        raise HTTPException(404, f"Run {run_id} not found")
    if state.get("workflow_status") not in ("awaiting_approval", "started", "starting"):
        raise HTTPException(
            400,
            f"Run {run_id} is not awaiting approval (status: {state.get('workflow_status')})",
        )

    workflow.set_approval_decision(run_id, req.offer_id, req.approved, req.reason)
    return {
        "run_id": run_id,
        "offer_id": req.offer_id,
        "decision": "approved" if req.approved else "rejected",
    }


@app.get("/api/run/{run_id}/state")
async def get_run_state(run_id: str):
    state = checkpoint.load(run_id)
    if not state:
        raise HTTPException(404, f"Run {run_id} not found")
    return state


@app.get("/health")
async def health():
    return {"status": "ok", "service": "sports-iq-agents"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Chat with the Foundry-hosted Fabric Data Agent.

    Supports multi-turn conversation via the Responses API's previous_response_id
    threading mechanism. Pass the response_id from the previous turn to maintain
    conversation context.

    Injects current game/stadium context so the Fabric Data Agent scopes
    redemption and offer queries to OfferFeedbackEvent (live) rather than
    promotion_history (historical seeded data).
    """
    from agents.shared import fabric_agent
    # Prepend game context on the first turn (no previous_response_id) so that
    # open-ended questions like "who redeemed offers" hit OfferFeedbackEvent
    # (current game, live) instead of promotion_history (all seeded history).
    if not req.previous_response_id:
        augmented_message = (
            f"[Context: gameId={config.DEMO_GAME_ID}, "
            f"stadiumId={config.DEMO_STADIUM_ID}] "
            f"{req.message}"
        )
    else:
        augmented_message = req.message
    try:
        answer, response_id = await asyncio.to_thread(
            fabric_agent.ask_chat, augmented_message, req.previous_response_id
        )
        return {"answer": answer, "response_id": response_id}
    except RuntimeError as exc:
        # FABRIC_DATA_AGENT_CONNECTION_NAME not configured
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        log.exception("Chat error")
        raise HTTPException(502, f"Fabric agent error: {exc}") from exc


@app.post("/api/demo/redeem-offer")
async def redeem_offer(req: RedeemOfferRequest):
    """SSE endpoint that simulates a Stadium POS redemption and closes the feedback loop.

    Yields step events:
      {"step": "scanning|eventhouse|lakehouse|complete", "status": "running|done|error",
       "message": str, "latency_ms"?: int, "transaction_id"?: str, "revenue_impact"?: float}
    """
    from agents.shared import eventhouse_client, lakehouse_client

    async def _generate() -> AsyncGenerator[str, None]:
        t_start = datetime.now(timezone.utc)

        def _emit(step: str, status: str, **kwargs) -> str:
            payload = {"step": step, "status": status, **kwargs}
            return f"data: {json.dumps(payload)}\n\n"

        # ── Step 1: Scanning QR / POS receipt ──
        yield _emit("scanning", "running", message="Stadium POS reading QR code on mobile offer…")
        await asyncio.sleep(1.0)

        # Compute discount and total
        offer_value = req.offer_value
        unit_price = req.unit_price
        if req.offer_type == "percentage_discount":
            discount = round(unit_price * offer_value / 100, 2)
        else:
            discount = round(offer_value, 2)
        total_amount = round(unit_price - discount, 2)
        revenue_impact = total_amount

        transaction_id = f"pos_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        tx = {
            "transactionId": transaction_id,
            "fanId": req.fan_id,
            "gameId": req.game_id,
            "transactionTimestamp": now_iso,
            "sourceSystem": "pos_system",
            "concessionZone": "ZONE_MERCH_1",
            "sectionId": req.section_id,
            "category": req.offer_category,
            "itemName": req.offer_title,
            "quantity": 1,
            "unitPrice": unit_price,
            "totalAmount": total_amount,
            "paymentMethod": "mobile_app",
            "offerRedeemed": True,
            "promoId": req.promo_id,
            "gameMinute": 65.0,
            "drive": 8,
            "quarter": 4,
        }

        t_scan = int((datetime.now(timezone.utc) - t_start).total_seconds() * 1000)
        yield _emit("scanning", "done", message="✅ QR code verified — offer accepted", latency_ms=t_scan,
                    transaction_id=transaction_id)
        await asyncio.sleep(0.5)

        # ── Step 2: Write to Eventhouse ──
        yield _emit("eventhouse", "running", message="Ingesting POSTransaction to Eventhouse (real-time)…")
        t_eh0 = datetime.now(timezone.utc)
        try:
            await asyncio.to_thread(
                eventhouse_client.ingest_pos_transaction,
                tx, config.EVENTHOUSE_URI, config.EVENTHOUSE_DB,
            )
            t_eh = int((datetime.now(timezone.utc) - t_eh0).total_seconds() * 1000)
            yield _emit("eventhouse", "done",
                        message=f"✅ Transaction landed in Eventhouse KQL table ({t_eh} ms)",
                        latency_ms=t_eh, transaction_id=transaction_id)
        except Exception as exc:
            log.exception("Eventhouse ingestion failed")
            yield _emit("eventhouse", "error", message=f"Eventhouse error: {exc}")
            return
        await asyncio.sleep(0.5)

        # ── Step 3: Write OfferFeedbackEvent back to Eventhouse (RTI closed loop) ──
        # The Lakehouse SQL Analytics Endpoint is read-only for Delta tables.
        # The feedback signal flows back through Eventhouse (correct RTI architecture).
        yield _emit("lakehouse", "running",
                    message="Writing OfferFeedbackEvent to Eventhouse (RTI feedback loop)…")
        t_fb0 = datetime.now(timezone.utc)
        try:
            fan_name = req.fan_name or req.fan_id
            trigger_ctx = (
                f"POS redemption by {fan_name} — {req.offer_title} "
                f"({req.offer_type.replace('_', ' ')}: {offer_value})"
            )
            feedback = {
                "feedbackId": f"fb_{uuid.uuid4().hex[:12]}",
                "promoId": req.promo_id,
                "fanId": req.fan_id,
                "gameId": req.game_id,
                "offerTimestamp": now_iso,
                "outcomeTimestamp": now_iso,
                "offerCategory": req.offer_category,
                "revenueImpact": revenue_impact,
                "gameMinute": 65.0,
                "drive": 8,
                "quarter": 4,
                "triggerContext": trigger_ctx,
            }
            await asyncio.to_thread(
                eventhouse_client.ingest_offer_feedback,
                feedback, config.EVENTHOUSE_URI, config.EVENTHOUSE_DB,
            )
            t_fb = int((datetime.now(timezone.utc) - t_fb0).total_seconds() * 1000)
            yield _emit("lakehouse", "done",
                        message=f"✅ OfferFeedbackEvent ingested — outcome=redeemed ({t_fb} ms)",
                        latency_ms=t_fb, revenue_impact=revenue_impact)
        except Exception as exc:
            log.exception("OfferFeedbackEvent ingestion failed")
            yield _emit("lakehouse", "error", message=f"Feedback event error: {exc}")
            return
        await asyncio.sleep(0.3)

        # ── Step 4: Lakehouse dual-write (Data Agent near-real-time visibility) ──
        # promotion_history: offer + outcome='redeemed'
        # pos_transaction:   linked actual purchase (linkedPromoId = promoId)
        # Requires a Fabric Warehouse endpoint (WAREHOUSE_SQL_ENDPOINT) — the Lakehouse
        # SQL Analytics Endpoint is read-only for Delta tables (error 24559).
        if config.WAREHOUSE_SQL_ENDPOINT:
            yield _emit("lakehouse_sync", "running",
                        message="Writing redemption to Warehouse (promotion_history + pos_transaction)…")
            t_lh0 = datetime.now(timezone.utc)
            try:
                await asyncio.to_thread(
                    lakehouse_client.record_offer_redemption,
                    fan_id=req.fan_id,
                    game_id=req.game_id,
                    promo_id=req.promo_id,
                    offer_category=req.offer_category,
                    offer_type=req.offer_type,
                    offer_value=float(req.offer_value),
                    revenue_impact=revenue_impact,
                    trigger_context=trigger_ctx,
                    sql_endpoint=config.WAREHOUSE_SQL_ENDPOINT,
                    database=config.WAREHOUSE_DB,
                    schema=config.WAREHOUSE_SCHEMA,
                )
                await asyncio.to_thread(
                    lakehouse_client.record_pos_transaction_lakehouse,
                    transaction_id=transaction_id,
                    fan_id=req.fan_id,
                    game_id=req.game_id,
                    offer_category=req.offer_category,
                    item_description=req.offer_title,
                    item_price=unit_price,
                    discount_applied=discount,
                    amount_paid=total_amount,
                    linked_promo_id=req.promo_id,
                    sql_endpoint=config.WAREHOUSE_SQL_ENDPOINT,
                    database=config.WAREHOUSE_DB,
                    schema=config.WAREHOUSE_SCHEMA,
                )
                t_lh = int((datetime.now(timezone.utc) - t_lh0).total_seconds() * 1000)
                yield _emit("lakehouse_sync", "done",
                            message=f"✅ Warehouse synced — Data Agent can now answer redemption queries ({t_lh} ms)",
                            latency_ms=t_lh)
            except Exception as exc:
                log.warning("Warehouse dual-write failed (non-fatal): %s", exc)
                yield _emit("lakehouse_sync", "error",
                            message=f"Warehouse sync failed (non-fatal — EventHouse RTI loop intact): {exc}")
            await asyncio.sleep(0.3)

        # ── Complete ──
        total_ms = int((datetime.now(timezone.utc) - t_start).total_seconds() * 1000)
        yield _emit(
            "complete", "done",
            message=(
                f"🎉 Redemption complete! ${revenue_impact:.2f} revenue captured in {total_ms} ms. "
                f'Ask the Data Agent: "What did {req.fan_name or req.fan_id} just buy?"'
            ),
            latency_ms=total_ms,
            transaction_id=transaction_id,
            revenue_impact=revenue_impact,
            suggested_question=(
                f'What is the latest purchase made by {req.fan_name or req.fan_id} '
                f'in game {req.game_id}? Show the offer redeemed and revenue impact.'
            ),
        )

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
