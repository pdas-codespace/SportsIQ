"""OfferApproverAgent — executes human-approved decisions: ACS email or rejection log.

HITL is handled at the WORKFLOW level (asyncio.Event pause between Generator and Approver).
This agent receives decisions already made and executes them using @tool functions.

Uses Microsoft Agent Framework: Agent + FoundryChatClient + @tool + AuditMiddleware.
"""
from __future__ import annotations
import logging
from typing import Annotated

from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential

from agents.shared import config, acs_client, lakehouse_client, teams_client
from agents.middleware import AuditFunctionMiddleware

log = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are the Sports-IQ Offer Approver.

You receive a list of offers along with human approval decisions that have ALREADY been made.
Execute each decision immediately without asking for further confirmation:
- APPROVED → call send_fan_notification() with the offer details.
- REJECTED → call log_rejection() with the offer_id and rejection reason.

After processing all offers, call post_teams_summary() to update the Teams channel.
Return a JSON summary of all actions taken.
"""


@tool
def send_fan_notification(
    offer_id: Annotated[str, "Unique offer identifier"],
    fan_email: Annotated[str, "Fan's email address"],
    fan_name: Annotated[str, "Fan's display name"],
    loyalty_tier: Annotated[str, "Fan loyalty tier (Bronze/Silver/Gold/Platinum)"],
    offer_title: Annotated[str, "Short offer title for the email subject"],
    offer_description: Annotated[str, "Full offer description for the email body"],
    offer_code: Annotated[str, "Promotional code to include in the email"],
) -> str:
    """Send the approved offer to the fan via ACS email."""
    # Guard: LLM sometimes passes empty string; fall back to demo constant
    if not fan_email:
        fan_email = config.DEMO_FAN_EMAIL
        log.warning("send_fan_notification: fan_email was empty, falling back to DEMO_FAN_EMAIL=%s", fan_email)
    if not config.ACS_CONNECTION_STRING:
        log.warning("ACS_CONNECTION_STRING not set — simulating email to %s", fan_email)
        return f"[SIMULATED] Email → {fan_email}: {offer_title} | Code: {offer_code}"
    log.info("ACS send_fan_notification: offer=%s to=%s sender=%s",
             offer_id, fan_email, config.ACS_SENDER_ADDRESS)
    try:
        msg_id = acs_client.send_offer_email(
            connection_string=config.ACS_CONNECTION_STRING,
            sender_address=config.ACS_SENDER_ADDRESS,
            to_email=fan_email,
            fan_name=fan_name,
            loyalty_tier=loyalty_tier,
            offer_title=offer_title,
            offer_description=offer_description,
            offer_code=offer_code,
        )
        log.info("ACS email accepted by server: message_id=%s offer=%s to=%s", msg_id, offer_id, fan_email)
        return f"Email sent. Message ID: {msg_id}"
    except Exception as exc:
        log.error("ACS send FAILED for offer=%s to=%s: %s", offer_id, fan_email, exc, exc_info=True)
        return f"Email failed: {exc}"


@tool
def log_rejection(
    offer_id: Annotated[str, "Unique offer identifier"],
    fan_id: Annotated[str, "Fan identifier"],
    game_id: Annotated[str, "Game identifier"],
    rejection_reason: Annotated[str, "Human-provided reason for rejecting the offer"],
) -> str:
    """Log a rejected offer to the Warehouse offer_decision_log table."""
    if not config.WAREHOUSE_SQL_ENDPOINT:
        return f"[SIMULATED] Rejection logged — {offer_id}: {rejection_reason}"
    lakehouse_client.log_offer_decision(
        offer_id=offer_id,
        fan_id=fan_id,
        game_id=game_id,
        decision="rejected",
        reason=rejection_reason,
        sql_endpoint=config.WAREHOUSE_SQL_ENDPOINT,
        database=config.WAREHOUSE_DB,
        schema=config.WAREHOUSE_SCHEMA,
    )
    return f"Rejection logged for {offer_id}. Reason: {rejection_reason}"


@tool
def post_teams_summary(
    fan_name: Annotated[str, "Fan display name"],
    game_label: Annotated[str, "Human-readable game label"],
    offers: Annotated[list, "List of offer dicts that were processed"],
    statuses: Annotated[dict, "Map of offer_id to decision status string"],
) -> str:
    """Post the final offer outcomes to the Teams channel via incoming webhook."""
    if not config.TEAMS_WEBHOOK_URL:
        return "[SIMULATED] Teams summary card would be posted."
    success = teams_client.post_offer_card(
        webhook_url=config.TEAMS_WEBHOOK_URL,
        fan_name=fan_name,
        game_label=game_label,
        offers=offers,
        statuses=statuses,
    )
    return "Teams card posted." if success else "Teams card post failed."


def create_agent(credential=None) -> Agent:
    """Create the MAF OfferApprover agent backed by a Foundry-hosted model."""
    cred = credential or DefaultAzureCredential()
    return Agent(
        client=FoundryChatClient(
            project_endpoint=config.FOUNDRY_PROJECT_ENDPOINT,
            model=config.FOUNDRY_MODEL,
            credential=cred,
        ),
        name="sports-iq-offer-approver",
        instructions=SYSTEM_PROMPT,
        tools=[send_fan_notification, log_rejection, post_teams_summary],
        middleware=[AuditFunctionMiddleware()],
    )
