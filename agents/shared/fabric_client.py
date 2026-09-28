"""Fabric Data Agent client — calls the MCP endpoint via JSON-RPC.

The Fabric MCP endpoint (/v1/mcp/.../agent) returns plain JSON for tools/call.
If the server returns text/event-stream, SSE parsing is applied as fallback.

Primary transport: FABRIC_DATA_AGENT_MCP_URL (JSON-RPC tools/call)
Fallback transport: FABRIC_DATA_AGENT_OPENAI_URL (OpenAI /chat/completions),
                    only if FABRIC_DATA_AGENT_OPENAI_URL is explicitly set.

Note: FABRIC_DATA_AGENT_URL (the aiassistant/openai URL) returns 404 for
      /chat/completions — do NOT use it as an OpenAI endpoint.
"""
from __future__ import annotations
import itertools
import json
import logging
import re
import requests
from azure.identity import DefaultAzureCredential
from opentelemetry import trace

log = logging.getLogger(__name__)

_credential = DefaultAzureCredential()
_FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
_counter = itertools.count(1)
_tracer = trace.get_tracer("sports-iq.fabric")

_MCP_TOOL_NAME = "DataAgent_SportsIQ_FanEngagement_DataAgent"


def _token() -> str:
    return _credential.get_token(_FABRIC_SCOPE).token


# ── Transport 1: OpenAI-compatible ────────────────────────────────────────────

def _ask_via_openai(question: str, openai_base_url: str, timeout: int = 60) -> str:
    """POST to {openai_base_url}/chat/completions and return the assistant message text."""
    url = openai_base_url.rstrip("/") + "/chat/completions"
    body = {"messages": [{"role": "user", "content": question}]}
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


# ── Transport 2: MCP JSON-RPC with SSE response ───────────────────────────────

def _parse_sse(text: str) -> dict:
    """Extract the first JSON-RPC message that contains 'result' or 'error' from SSE text."""
    for line in text.splitlines():
        if not line.startswith("data:"):
            continue
        payload_str = line[5:].strip()
        if not payload_str:
            continue
        try:
            obj = json.loads(payload_str)
            if "result" in obj or "error" in obj:
                return obj
        except json.JSONDecodeError:
            continue
    raise RuntimeError(f"No JSON-RPC result found in SSE response: {text[:400]}")


def _ask_via_mcp(question: str, mcp_url: str, timeout: int = 60) -> str:
    """POST a JSON-RPC tools/call to the MCP endpoint and handle SSE or JSON response."""
    body = {
        "jsonrpc": "2.0",
        "id": next(_counter),
        "method": "tools/call",
        "params": {
            "name": _MCP_TOOL_NAME,
            "arguments": {"userQuestion": question},
        },
    }
    resp = requests.post(
        mcp_url,
        headers={
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
            # Accept both plain JSON and SSE streaming
            "Accept": "application/json, text/event-stream",
        },
        json=body,
        timeout=timeout,
    )
    resp.raise_for_status()

    content_type = resp.headers.get("content-type", "")
    if "text/event-stream" in content_type:
        payload = _parse_sse(resp.text)
    else:
        payload = resp.json()

    if "error" in payload:
        raise RuntimeError(f"MCP error: {payload['error']}")

    result = payload.get("result", {})
    content = result.get("content", [])
    texts = [block["text"] for block in content if block.get("type") == "text"]
    return "\n".join(texts) if texts else str(result)


# ── Public API ─────────────────────────────────────────────────────────────────

def ask(question: str, endpoint_url: str = "", timeout: int = 60) -> str:
    """Ask the Fabric Data Agent a natural language question via MCP tools/call.

    The Fabric MCP endpoint (/agent) returns plain JSON (not SSE).
    Falls back to SSE parsing if the server returns text/event-stream.

    URL resolution (priority):
      1. explicit endpoint_url argument
      2. FABRIC_DATA_AGENT_MCP_URL in .env  (preferred)
      3. FABRIC_DATA_AGENT_OPENAI_URL via _ask_via_openai (if explicitly set)
    """
    with _tracer.start_as_current_span("fabric_da.ask") as span:
        span.set_attribute("fabric.question", question[:200])
        try:
            from agents.shared import config as _cfg

            mcp_url = endpoint_url or _cfg.FABRIC_DATA_AGENT_MCP_URL
            openai_url = _cfg.FABRIC_DATA_AGENT_OPENAI_URL  # only if explicitly set

            if mcp_url:
                span.set_attribute("fabric.transport", "mcp")
                span.set_attribute("fabric.url", mcp_url)
                answer = _ask_via_mcp(question, mcp_url, timeout)
            elif openai_url:
                span.set_attribute("fabric.transport", "openai")
                span.set_attribute("fabric.url", openai_url)
                answer = _ask_via_openai(question, openai_url, timeout)
            else:
                raise RuntimeError(
                    "No Fabric Data Agent URL configured. "
                    "Set FABRIC_DATA_AGENT_MCP_URL in .env"
                )

            span.set_attribute("fabric.response_length", len(answer))
            span.set_status(trace.StatusCode.OK)
            return answer
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.StatusCode.ERROR, str(exc))
            raise


def get_fan_context(fan_id: str, game_id: str, endpoint_url: str = "") -> str:
    """Ask the Fabric Data Agent for full fan context for offer generation."""
    q = (
        f"For fan {fan_id} and game {game_id}: "
        "return their loyalty tier, average spend per game, average concession spend, "
        "average merchandise spend, offer fatigue gap minutes, base engagement score, "
        "churn risk score, last 3 redeemed offers (category, value, outcome), "
        "and any active stadium incidents near their section. "
        "Format as a structured summary."
    )
    return ask(q, endpoint_url)


def search_fans_by_tier(tier: str, endpoint_url: str = "") -> list[dict]:
    """Return all fans in a loyalty tier with offer-fatigue status, via the Data Agent."""
    q = (
        f"From the fan_profile table, get all fans with loyaltyTier = '{tier}'. "
        "For each fan join with the promotion_history table (on fanId) to find their most recent offer date. "
        "Compute offerFatigued = true if DATEDIFF(minute, lastOfferTimestamp, GETDATE()) < offerFatigueGapMinutes "
        "(treat fans with no offer history as NOT fatigued). "
        "Return ONLY a valid JSON array — no markdown, no explanation — where each element has: "
        "fanId (string), fanName (string, use fanId if no name column exists), "
        "loyaltyTier (string), preferredSectionId (string), "
        "baseEngagementScore (float 0-1), lastOfferDaysAgo (integer, -1 if never received an offer), "
        "offerFatigued (boolean)."
    )
    return _parse_fan_list(ask(q, endpoint_url))


def search_fans_by_sections(section_ids: list[str], endpoint_url: str = "") -> list[dict]:
    """Return all fans whose preferredSectionId is in the given list, with offer-fatigue status."""
    sections_csv = ", ".join(f"'{s}'" for s in section_ids)
    q = (
        f"From the fan_profile table, get all fans with preferredSectionId IN ({sections_csv}). "
        "For each fan join with the promotion_history table (on fanId) to find their most recent offer date. "
        "Compute offerFatigued = true if DATEDIFF(minute, lastOfferTimestamp, GETDATE()) < offerFatigueGapMinutes "
        "(treat fans with no offer history as NOT fatigued). "
        "Return ONLY a valid JSON array — no markdown, no explanation — where each element has: "
        "fanId (string), fanName (string, use fanId if no name column exists), "
        "loyaltyTier (string), preferredSectionId (string), "
        "baseEngagementScore (float 0-1), lastOfferDaysAgo (integer, -1 if never received an offer), "
        "offerFatigued (boolean)."
    )
    return _parse_fan_list(ask(q, endpoint_url))


def _parse_fan_list(raw: str) -> list[dict]:
    """Extract a JSON array from the Data Agent's response text."""
    # Try direct parse first
    try:
        result = json.loads(raw.strip())
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    # Extract first [...] block from mixed text/markdown response
    match = re.search(r"\[.*?\]", raw, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
    log.warning("fabric_client: could not parse fan list from Data Agent response: %s", raw[:300])
    return []
