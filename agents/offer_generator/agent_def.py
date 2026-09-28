"""OfferGeneratorAgent — produces 2 personalized ranked offers using fan + game context.

Uses Microsoft Agent Framework: Agent + FoundryChatClient + @tool.
Fan context is fetched via a Foundry-hosted agent with MicrosoftFabricPreviewTool,
which provides identity-passthrough access to the Fabric Data Agent.
"""
from __future__ import annotations
import json
from typing import Annotated

from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential

from agents.shared import config, fabric_agent, lakehouse_client
from agents.middleware import AuditFunctionMiddleware, PolicyGuardrailMiddleware


SYSTEM_PROMPT = """You are the Sports-IQ Offer Generator for live sports fans.

Given a fan context payload from the Engagement Monitor, your job:
1. Retrieve full fan context from the Fabric Data Agent.
2. Check for active stadium incidents in the fan's section.
3. Get available merchandise inventory at the stadium.
4. Generate exactly 2 personalized offers ranked by expected redemption probability:
   - Offer A: the best-fit intervention for this specific fan, tier, section, and urgency.
   - Offer B: a secondary alternative that is meaningfully different from Offer A.

Do NOT reuse the same generic jersey + concession pair for every fan. Vary the
primary offer by tier, location, purchase mix, and engagement urgency:
- Lower Deck / S112 Gold fans: favor nearby concession or combo offers.
- Platinum / Field Level / VIP fans: favor premium, limited-edition, or club-level offers.
- End Zone / Merch Hub fans: favor merchandise offers tied to nearby inventory.
- Silver or high churn-risk fans: favor higher-urgency re-engagement vouchers.

Use the sport_context payload as the only source of user-facing league, team,
venue, and merchandise branding. If a tool returns labels that conflict with
the selected sport or team, do not use them in titles, descriptions,
justifications, or offer codes.

For each offer output:
{
  "id": "offer_<uuid>",
  "title": "...",
  "description": "...",
  "category": "merchandise" | "food_beverage",
  "offer_type": "percentage_discount" | "fixed_amount",
  "value": "20%" | "$5.00",
  "offer_code": "<home_team>-XXXXX",
  "justification": "1-sentence reason based on purchase history",
  "incident_alert": null | "Active crowd disturbance S110-S114 — F&B offers may be inappropriate"
}

IMPORTANT: If an active stadium incident affects the fan's section AND blocks food_beverage offers,
set incident_alert on Offer B. Do NOT suppress the offer — let the human reviewer decide.
The incident information is presented to the human to inform their decision.

Return your final answer as:
{ "offers": [<Offer A>, <Offer B>] }
"""


def build_offer_generation_prompt(
    *,
    fan_id: str,
    game_id: str,
    section_id: str,
    stadium_id: str,
    monitor_data: dict,
    fan_name: str = "",
    fan_loyalty_tier: str = "",
    sport_context: dict | None = None,
) -> str:
    """Build the OfferGenerator prompt with selected-fan tier and section context."""
    sport = sport_context or config.default_sport_context()
    context = {
        "fan_id": fan_id,
        "game_id": game_id,
        "section_id": section_id,
        "stadium_id": stadium_id,
        "sport_context": sport,
        "selected_fan": {
            "fan_name": fan_name,
            "loyalty_tier": fan_loyalty_tier,
            "preferred_section_id": section_id,
        },
        "monitor_context": monitor_data,
        "personalization_rules": [
            "Use section_id as the fan's current seat/location when calling incident tools.",
            "Use loyalty_tier to tune urgency, value, and premium positioning.",
            "Use sport_context.home_team_name and sport_context.home_team for all team merchandise and offer codes.",
            "Do not introduce team branding or sport-specific terms that conflict with sport_context.",
            "Return two offers, but make the first offer the best fit for this fan's story.",
            "Do not return the same generic jersey and food/beverage discount pair for every fan.",
        ],
    }
    return (
        "Generate exactly 2 ranked, personalized offers for the selected fan. "
        "Context: " + json.dumps(context)
    )


@tool
def get_fan_context(
    fan_id: Annotated[str, "The fan's unique identifier"],
    game_id: Annotated[str, "The game's unique identifier"],
) -> str:
    """Retrieve fan profile, purchase history, and game context via the Foundry Fabric agent."""
    import logging
    log = logging.getLogger(__name__)

    if config.FABRIC_DATA_AGENT_CONNECTION_NAME:
        try:
            return fabric_agent.get_fan_context(fan_id, game_id)
        except Exception as exc:
            log.warning("Foundry Fabric agent unavailable (%s) — falling back to Lakehouse", exc)
    elif config.FABRIC_DATA_AGENT_MCP_URL:
        try:
            from agents.shared import fabric_client
            return fabric_client.get_fan_context(fan_id, game_id)
        except Exception as exc:
            log.warning("Fabric MCP unavailable (%s) — falling back to Lakehouse", exc)

    # Final fallback: direct Lakehouse SQL
    profile = lakehouse_client.get_fan_profile(
        fan_id, config.LAKEHOUSE_SQL_ENDPOINT, config.LAKEHOUSE_DB, config.LAKEHOUSE_SCHEMA
    )
    return str(profile) if profile else f"Fan {fan_id} not found"


@tool
def get_active_stadium_incidents(
    section_id: Annotated[str, "The stadium section ID to check for active incidents"],
) -> list:
    """Check for active stadium incidents affecting the given section."""
    return lakehouse_client.get_active_incidents(
        section_id, config.LAKEHOUSE_SQL_ENDPOINT, config.LAKEHOUSE_DB, config.LAKEHOUSE_SCHEMA
    )


@tool
def get_merchandise_inventory(
    stadium_id: Annotated[str, "The stadium identifier"],
) -> list:
    """Get available merchandise items currently in stock at the stadium."""
    return lakehouse_client.get_merch_inventory(
        stadium_id, config.LAKEHOUSE_SQL_ENDPOINT, config.LAKEHOUSE_DB, config.LAKEHOUSE_SCHEMA
    )


def create_agent(credential=None) -> Agent:
    """Create the MAF OfferGenerator agent backed by a Foundry-hosted model."""
    cred = credential or DefaultAzureCredential()
    return Agent(
        client=FoundryChatClient(
            project_endpoint=config.FOUNDRY_PROJECT_ENDPOINT,
            model=config.FOUNDRY_MODEL,
            credential=cred,
        ),
        name="sports-iq-offer-generator",
        instructions=SYSTEM_PROMPT,
        tools=[get_fan_context, get_active_stadium_incidents, get_merchandise_inventory],
        middleware=[AuditFunctionMiddleware(), PolicyGuardrailMiddleware()],
    )
