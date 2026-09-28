"""Foundry-hosted Fabric context agent.

Creates a Foundry Prompt Agent with MicrosoftFabricPreviewTool that routes
natural language questions to the Fabric Data Agent with identity passthrough.

Set in .env:
  FABRIC_DATA_AGENT_CONNECTION_NAME = full resource ID of the Foundry project
  connection to the Fabric Data Agent, e.g.:
  /subscriptions/.../providers/Microsoft.CognitiveServices/accounts/.../
  projects/.../connections/<connectionName>

The agent is created once (or reused if it already exists) and cached for the
lifetime of the process.
"""
from __future__ import annotations
import logging
import re
from functools import lru_cache
from urllib.parse import urlparse
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    MicrosoftFabricPreviewTool,
    FabricDataAgentToolParameters,
    ToolProjectConnection,
    MCPTool
)
from opentelemetry import trace

log = logging.getLogger(__name__)
_tracer = trace.get_tracer("sports-iq.fabric-agent")

AGENT_NAME = "sports-iq-fabric-context-agent-v7"
_INSTRUCTIONS = (
    "You are the Sports-IQ Fan Context Agent — a Fabric data analyst for a live "
    "sporting event fan engagement platform (works across multiple sports). "
    "Use the Fabric Data Agent tool to answer questions about fan profiles, "
    "purchase history, offer/redemption history, and game context.\n\n"

    "## Context Routing — CRITICAL\n"
    "You receive a [Context: gameId=..., stadiumId=...] header with questions.\n"
    "This tells you the CURRENT game. YOU decide query scope based on intent:\n\n"
    "- LIVE intent ('redeemed today', 'this game', 'current', 'right now', 'so far'):\n"
    "  → Pass gameId filter to the Fabric Data Agent query\n"
    "- HISTORICAL/ANALYTICAL intent ('received', 'history', 'across games', "
    "'top fans by churn', 'revenue at risk', 'which sections', 'all time', "
    "'highest-churn', 'Silver fans', 'Platinum fans'):\n"
    "  → Do NOT filter by gameId. Query across all games.\n"
    "- MIXED intent ('compare today vs last 3 games'):\n"
    "  → Make two calls: one with gameId (live), one without (historical)\n\n"
    "The [Context] header is INFORMATIONAL, not a mandatory filter.\n\n"

    "## Table Routing — CRITICAL\n"
    "AUTHORITATIVE SOURCE for all offer/redemption questions:\n"
    "  → OfferFeedbackEvent (Eventhouse shortcut) — ALWAYS query this FIRST\n"
    "AUTHORITATIVE SOURCE for all purchase/transaction/concession questions:\n"
    "  → POSTransaction (Eventhouse shortcut) — ALWAYS query this FIRST\n"
    "  For concession zone activity: GROUP BY category or zone fields in POSTransaction,\n"
    "  then enrich zone names/operators from sportsiq-aisearch-source knowledge base.\n\n"
    "DEPRECATED — query ONLY if OfferFeedbackEvent returns 0 rows for that fan:\n"
    "  → promotion_history (stale seeded data)\n"
    "NEVER USE:\n"
    "  → pos_transaction (broken sync, stale data)\n\n"
    "REFERENCE tables (always available):\n"
    "  fan_profile, fan_contact, game_context, engagement_pattern, "
    "stadium_incident, merchandise_inventory\n\n"

    "## Domain Entities\n"
    "Fan (fan_profile + ontology Fan entity), Game (game_context + ontology Game entity), "
    "SeatSection (ontology entity), Offer (OfferFeedbackEvent), "
    "Purchase (POSTransaction), Incident (stadium_incident), "
    "Merchandise (merchandise_inventory — catalog only).\n\n"

    "## Computed Metrics\n"
    "- offerEligibility: ELIGIBLE if mins_since_last_offer >= offerFatigueGapMinutes, else SUPPRESSED\n"
    "- churnRiskLevel: CRITICAL (>0.7), HIGH (>0.5), MEDIUM (>0.3), LOW (<=0.3)\n"
    "- interventionPriority: URGENT (declining + high churn), ELEVATED, NORMAL\n\n"

    "## Knowledge Sources\n"
    "You have access to TWO knowledge sources — always combine both when relevant:\n"
    "- Configured weather knowledge source: real-time weather data\n"
    "- Configured venue knowledge source: layout and concessions across seating levels "
    "with capacity, concession zone mapping, walk times, and weather exposure. "
    "Full concession zone operator map, 11-item core menu with price ranges and prep times.\n\n"
    "For weather questions: find the stadium venue info (State and City) from "
    "the venue knowledge source FIRST, then fetch weather from the configured weather source "
    "for that specific city/state only. Do NOT fetch weather for irrelevant locations.\n\n"
    "For concession zone questions ('most active zones', 'busiest concessions', 'zone revenue'):\n"
    "  1. Query POSTransaction (Fabric Data Agent) to get transaction counts/revenue by zone\n"
    "  2. Enrich with the venue knowledge source for zone names, operators, locations, menu items\n"
    "  3. Combine both sources in your response\n\n"

    "## Rules\n"
    "- NEVER use merchandise_inventory or engagement_pattern as a proxy for purchases.\n"
    "- offerValue = discount shown to fan. revenueImpact = resulting revenue. Do NOT confuse them.\n"
    "- Return structured, factual answers only — no speculation or invented fan names.\n"
    "- When asked about 'offers received' or 'did they redeem', query OfferFeedbackEvent "
    "not promotion_history.\n"
    "- Stick to the task and provide response that is relevant to the question asked."
)

# Module-level cache: set after first successful ensure_agent()
_agent_name_cache: str | None = None


def _knowledge_base_tool(
    search_service_endpoint: str,
    knowledgebase_name: str,
    connection_name: str,
) -> MCPTool | None:
    """Build the optional Foundry IQ MCP tool when fully configured."""
    values = (search_service_endpoint, knowledgebase_name, connection_name)
    if not any(values):
        return None
    if not all(values):
        log.warning("Foundry IQ MCP tool disabled: configuration is incomplete")
        return None

    endpoint = search_service_endpoint.strip().rstrip("/")
    parsed_endpoint = urlparse(endpoint)
    if parsed_endpoint.scheme not in {"http", "https"} or not parsed_endpoint.netloc:
        log.warning(
            "Foundry IQ MCP tool disabled: search service endpoint must be an absolute HTTP(S) URL"
        )
        return None

    # No GoF pattern applies: this is configuration validation and tool assembly.
    return MCPTool(
        server_label="knowledge-base",
        server_url=(
            f"{endpoint}/knowledgebases/{knowledgebase_name}"
            "/mcp?api-version=2026-05-01-preview"
        ),
        require_approval="never",
        allowed_tools=["knowledge_base_retrieve"],
        project_connection_id=connection_name,
    )


@lru_cache(maxsize=1)
def _project() -> AIProjectClient:
    from agents.shared import config
    return AIProjectClient(
        endpoint=config.FOUNDRY_PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )


def ensure_agent() -> str:
    """Create the Fabric context agent in Foundry if it doesn't already exist.

    Returns the agent name. Safe to call multiple times — reuses existing agent.
    """
    global _agent_name_cache
    if _agent_name_cache:
        return _agent_name_cache

    from agents.shared import config
    connection_id = config.FABRIC_DATA_AGENT_CONNECTION_NAME
    if not connection_id:
        raise RuntimeError(
            "FABRIC_DATA_AGENT_CONNECTION_NAME not configured in .env. "
            "Get it from Foundry portal → Management center → Connected resources."
        )

    project = _project()

    fabric_tool = MicrosoftFabricPreviewTool(
        fabric_dataagent_preview=FabricDataAgentToolParameters(
            project_connections=[
                ToolProjectConnection(project_connection_id=connection_id)
            ]
        )
    )
    tools = [fabric_tool]
    knowledge_base_tool = _knowledge_base_tool(
        config.FOUNDRY_IQ_SEARCH_SERVICE_ENDPOINT,
        config.FOUNDRY_IQ_KNOWLEDGEBASE_NAME,
        config.FOUNDRY_IQ_CONNECTION_NAME,
    )
    if knowledge_base_tool is not None:
        tools.append(knowledge_base_tool)

    agent = project.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=config.FOUNDRY_MODEL,
            instructions=_INSTRUCTIONS,
            tools=tools,
            
        ),
    )
    log.info("Created Foundry Fabric context agent: %s", AGENT_NAME)
    _agent_name_cache = agent.name
    return agent.name


def _call_agent(question: str, previous_response_id: str | None = None) -> tuple[str, str]:
    """Low-level call to the Foundry-hosted agent. Returns (answer, response_id)."""
    agent_name = ensure_agent()
    project = _project()
    openai_client = project.get_openai_client()

    kwargs: dict = {
        "tool_choice": "required",
        "input": question,
        "extra_body": {
            "agent_reference": {
                "name": agent_name,
                "type": "agent_reference",
            }
        },
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id

    # Wrap the Responses API call in a named span so the MAF-generated
    # "execute_tool remote_functions.azure_fabric" dependency becomes a
    # child of this span 
    with _tracer.start_as_current_span(
        "foundry.invoke_fabric_data_agent",
        attributes={
            "ai.agent.name": agent_name,
            "ai.tool.name": "remote_functions.azure_fabric",
            "ai.question.preview": question[:200],
            "ai.threaded": previous_response_id is not None,
        },
    ):
        response = openai_client.responses.create(**kwargs)
    answer = re.sub(r'【\d+:\d+†[^】]*】', '', response.output_text).strip()
    return answer, response.id


def ask(question: str) -> str:
    """Ask the Fabric Data Agent a question via the Foundry-hosted Fabric agent."""
    with _tracer.start_as_current_span("fabric_agent.ask") as span:
        span.set_attribute("fabric.agent.question", question[:200])
        try:
            answer, _ = _call_agent(question)
            span.set_attribute("fabric.agent.response_length", len(answer))
            span.set_status(trace.StatusCode.OK)
            return answer
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.StatusCode.ERROR, str(exc))
            raise


def ask_chat(question: str, previous_response_id: str | None = None) -> tuple[str, str]:
    """Ask a chat question with optional conversation threading.

    Args:
        question: The user's question.
        previous_response_id: Responses API ID from the prior turn for multi-turn context.

    Returns:
        (answer, response_id) — response_id should be passed back as previous_response_id
        on the next turn to maintain conversation context.
    """
    with _tracer.start_as_current_span("fabric_agent.ask_chat") as span:
        span.set_attribute("fabric.agent.question", question[:200])
        span.set_attribute("fabric.agent.threaded", previous_response_id is not None)
        try:
            answer, response_id = _call_agent(question, previous_response_id)
            span.set_attribute("fabric.agent.response_length", len(answer))
            span.set_attribute("fabric.agent.response_id", response_id)
            span.set_status(trace.StatusCode.OK)
            return answer, response_id
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.StatusCode.ERROR, str(exc))
            raise


def get_fan_context(fan_id: str, game_id: str) -> str:
    """Get full fan profile + purchase history context for offer generation."""
    q = (
        f"For fan {fan_id} in game {game_id}: "
        "return their loyalty tier, average spend per game, average concession spend, "
        "average merchandise spend, offer fatigue gap minutes, base engagement score, "
        "churn risk score, last 3 redeemed offers (category, value, outcome), "
        "and any active stadium incidents near their section. "
        "Format as a structured summary."
    )
    return ask(q)
