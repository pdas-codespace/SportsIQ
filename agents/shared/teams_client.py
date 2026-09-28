"""Teams incoming webhook client — posts Adaptive Card for offer notification."""
from __future__ import annotations
import requests


def _build_offer_block(offer: dict, status: str) -> dict:
    status_color = {
        "pending": "Default",
        "approved": "Good",
        "rejected": "Attention",
    }.get(status, "Default")

    status_emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(status, "")
    incident_block = []
    if offer.get("incident_alert"):
        incident_block = [{
            "type": "TextBlock",
            "text": f"🚨 {offer['incident_alert']}",
            "color": "Attention",
            "wrap": True,
            "size": "Small",
        }]

    return {
        "type": "Container",
        "style": "emphasis",
        "items": [
            {"type": "TextBlock", "text": f"{status_emoji} {offer['title']}", "weight": "Bolder", "size": "Medium"},
            {"type": "TextBlock", "text": offer["description"], "wrap": True, "color": status_color},
            *incident_block,
            {"type": "FactSet", "facts": [
                {"title": "Value", "value": offer.get("value", "")},
                {"title": "Category", "value": offer.get("category", "")},
                {"title": "Reason", "value": offer.get("justification", "")},
            ]},
        ],
    }


def post_offer_card(
    webhook_url: str,
    fan_name: str,
    game_label: str,
    offers: list[dict],
    statuses: dict[str, str] | None = None,
) -> bool:
    """
    Post an Adaptive Card to a Teams channel.
    offers: list of offer dicts with keys: id, title, description, value, category, justification, incident_alert
    statuses: {offer_id: 'pending'|'approved'|'rejected'}
    """
    if not webhook_url:
        return False

    statuses = statuses or {}
    offer_blocks = [_build_offer_block(o, statuses.get(o["id"], "pending")) for o in offers]

    card = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.5",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "🏈 Sports-IQ: Fan Offers Pending Review",
                        "size": "Large",
                        "weight": "Bolder",
                        "color": "Accent",
                    },
                    {
                        "type": "TextBlock",
                        "text": f"**{fan_name}** · Gold Tier · Section 112 · {game_label}",
                        "wrap": True,
                        "spacing": "None",
                    },
                    {"type": "Separator"},
                    *offer_blocks,
                    {
                        "type": "TextBlock",
                        "text": "_Review and respond in the Sports-IQ demo app._",
                        "isSubtle": True,
                        "wrap": True,
                        "size": "Small",
                    },
                ],
            },
        }],
    }
    resp = requests.post(webhook_url, json=card, timeout=10)
    return resp.status_code in (200, 202)
