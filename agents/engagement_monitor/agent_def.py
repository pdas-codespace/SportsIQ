"""EngagementMonitorAgent — detects engagement drops and checks offer fatigue gate.

Uses Microsoft Agent Framework: Agent + FoundryChatClient + @tool + AuditMiddleware.
"""
from __future__ import annotations
from typing import Annotated

from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential

from agents.shared import config, eventhouse_client, lakehouse_client
from agents.middleware import AuditFunctionMiddleware


SYSTEM_PROMPT = """You are the Sports-IQ Engagement Monitor.

Your job:
1. Query the latest fan engagement event for the target fan and game.
2. Determine if the fan needs intervention using EITHER condition:
   a. Engagement score is below 0.55 (absolute low engagement), OR
   b. Engagement score has dropped significantly — Platinum fans drop below 0.65,
      Gold below 0.55, Silver/Bronze below 0.45 are all considered disengaged.
3. Run the offer fatigue guard: verify the fan is eligible (enough time since last offer).
4. If both conditions pass, output a structured fan context payload for the Offer Generator.

If source is "lakehouse_fallback" in the engagement result, note that no live event was found
and the baseline score is being used — this is normal during demo setup.

Always call the tools provided. Do not guess values.
Return your final answer as a JSON object:
{
  "should_generate_offers": true/false,
  "reason": "...",
  "fan_id": "...",
  "game_id": "...",
  "engagement_score": 0.0,
  "fatigue_eligible": true/false,
  "game_moment": "Q2 commercial break",
  "loyalty_tier": "Gold",
  "quarter": 2,
  "minutesSinceLastOffer": 35,
  "totalOffersThisGame": 1,
  "totalOfferValueThisGame": 15.00,
  "gameExcitementIndex": 0.55,
  "isRedZone": false,
  "lastPlayType": null,
  "timeSinceTD": null,
  "down": null,
  "scoreDifferential": null,
  "gameClockQ2LessThan2m30s": false,
  "activeIncident": null
}

Notes on the extended fields:
- "quarter": from query_current_engagement result (use null if not in event)
- "minutesSinceLastOffer": from check_offer_fatigue_guard result (minutes since last offer)
- "totalOffersThisGame": from check_offer_fatigue_guard (count of offers sent this game)
- "totalOfferValueThisGame": from check_offer_fatigue_guard (summed offer value this game)
- "gameExcitementIndex": same as engagement_score (alias for policy guardrail use)
- "isRedZone", "lastPlayType", "timeSinceTD", "down", "scoreDifferential",
  "gameClockQ2LessThan2m30s": set to null — these require deeper game state not yet in
  the engagement event (will be added in a future Eventhouse integration phase)
- "activeIncident": set to null unless you have explicit incident data
"""


@tool
def query_current_engagement(
    fan_id: Annotated[str, "The fan's unique identifier"],
    game_id: Annotated[str, "The game's unique identifier"],
) -> dict:
    """Query the latest engagement event for a fan in a game from Eventhouse KQL.
    Falls back to the fan's baseEngagementScore from Lakehouse if no KQL event exists yet."""
    result = eventhouse_client.get_latest_engagement(
        fan_id, game_id, config.EVENTHOUSE_URI, config.EVENTHOUSE_DB
    )
    if result is not None:
        return {"found": True, "source": "eventhouse", **result}

    # No KQL event — fall back to Lakehouse baseEngagementScore so the demo
    # works before events are streamed into Eventhouse.
    profile = lakehouse_client.get_fan_profile(
        fan_id, config.LAKEHOUSE_SQL_ENDPOINT, config.LAKEHOUSE_DB, config.LAKEHOUSE_SCHEMA
    )
    if profile:
        base_score = float(profile.get("baseEngagementScore") or 0.5)
        return {
            "found": True,
            "source": "lakehouse_fallback",
            "fan_id": fan_id,
            "game_id": game_id,
            "engagementScore": base_score,
            "eventType": "baseline",
            "dwellSeconds": 0,
            "screenName": "",
            "quarter": 2,
            "gameMinute": 30.0,
            "eventTimestamp": None,
            "note": "No live event found — using fan baseline engagement score from Lakehouse.",
        }
    return {"found": False, "fan_id": fan_id, "game_id": game_id}


@tool
def check_offer_fatigue_guard(
    fan_id: Annotated[str, "The fan's unique identifier"],
) -> dict:
    """Check if the fan is eligible for a new offer based on the fatigue guard rules."""
    return lakehouse_client.get_offer_fatigue_status(
        fan_id, config.LAKEHOUSE_SQL_ENDPOINT, config.LAKEHOUSE_DB, config.LAKEHOUSE_SCHEMA
    )


def create_agent(credential=None) -> Agent:
    """Create the MAF EngagementMonitor agent backed by a Foundry-hosted model."""
    cred = credential or DefaultAzureCredential()
    return Agent(
        client=FoundryChatClient(
            project_endpoint=config.FOUNDRY_PROJECT_ENDPOINT,
            model=config.FOUNDRY_MODEL,
            credential=cred,
        ),
        name="sports-iq-engagement-monitor",
        instructions=SYSTEM_PROMPT,
        tools=[query_current_engagement, check_offer_fatigue_guard],
        middleware=[AuditFunctionMiddleware()],
    )
