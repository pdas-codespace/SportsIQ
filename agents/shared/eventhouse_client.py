"""Eventhouse (Kusto) REST client — no SDK install needed, uses DefaultAzureCredential."""
from __future__ import annotations
import json as _json
import logging
import requests
from azure.identity import DefaultAzureCredential

log = logging.getLogger(__name__)
_credential = DefaultAzureCredential()
_KUSTO_AUDIENCE = "https://kusto.kusto.windows.net/.default"


def _token() -> str:
    return _credential.get_token(_KUSTO_AUDIENCE).token


def run_query(query: str, cluster_uri: str, database: str) -> list[dict]:
    """Execute a KQL query and return rows as a list of dicts."""
    resp = requests.post(
        f"{cluster_uri}/v1/rest/query",
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
        json={"db": database, "csl": query},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    table = data["Tables"][0]
    columns = [c["ColumnName"] for c in table["Columns"]]
    return [dict(zip(columns, row)) for row in table["Rows"]]


def get_latest_engagement(fan_id: str, game_id: str, cluster_uri: str, database: str) -> dict | None:
    """Return the most recent FanEngagementEvent for a fan in the current game."""
    query = f"""
    FanEngagementEvent
    | where fanId == '{fan_id}' and gameId == '{game_id}'
    | order by eventTimestamp desc
    | take 1
    | project fanId, gameId, eventTimestamp, engagementScore, eventType, dwellSeconds, screenName, quarter, gameMinute
    """
    rows = run_query(query, cluster_uri, database)
    return rows[0] if rows else None


def scan_disengaged_fans(game_id: str, cluster_uri: str, database: str) -> list[dict]:
    """Return the latest engagement score per fan in the game, sorted ascending (most disengaged first)."""
    query_str = f"""
    FanEngagementEvent
    | where gameId == '{game_id}'
    | summarize arg_max(eventTimestamp, *) by fanId
    | project fanId, engagementScore, quarter, gameMinute, sectionId, eventTimestamp
    | order by engagementScore asc
    """
    return run_query(query_str, cluster_uri, database)


def get_recent_pos_transactions(fan_id: str, game_id: str, cluster_uri: str, database: str) -> list[dict]:
    """Return POS transactions for the fan in the current game."""
    query = f"""
    POSTransaction
    | where fanId == '{fan_id}' and gameId == '{game_id}'
    | order by transactionTimestamp desc
    | project transactionId, category, itemName, amount, quantity, transactionTimestamp
    """
    return run_query(query, cluster_uri, database)


def ingest_pos_transaction(tx: dict, cluster_uri: str, database: str) -> None:
    """Write a single POS transaction directly to Eventhouse via KQL .set-or-append.

    Uses the management endpoint so the row is immediately queryable (no Eventstream
    pipeline delay). Designed for demo closed-loop simulation.

    Args:
        tx: Dict with keys matching the POSTransaction table schema (see create_kql_tables.kql).
        cluster_uri: Eventhouse cluster URI from config.EVENTHOUSE_URI.
        database: KQL database name from config.EVENTHOUSE_DB.
    """
    def _esc(v: object) -> str:
        """Escape string for embedding in a KQL string literal."""
        return str(v).replace("\\", "\\\\").replace('"', '\\"') if v is not None else ""

    # Keep the Z suffix — KQL datetime literals accept ISO 8601 with Z
    ts_str = str(tx.get("transactionTimestamp", ""))
    promo_id = _esc(tx.get("promoId") or "")

    # Build a single-row .set-or-append using a datatable literal.
    # Schema mirrors create_kql_tables.kql exactly — column order matters.
    csl = (
        ".set-or-append POSTransaction <|\n"
        "datatable(\n"
        "    transactionId:string, fanId:string, gameId:string, transactionTimestamp:datetime,\n"
        "    sourceSystem:string, concessionZone:string, sectionId:string, category:string,\n"
        "    itemName:string, quantity:int, unitPrice:real, totalAmount:real,\n"
        "    paymentMethod:string, offerRedeemed:bool, promoId:string,\n"
        "    gameMinute:real, drive:int, quarter:int\n"
        ")[\n"
        f'"{_esc(tx["transactionId"])}", "{_esc(tx["fanId"])}", "{_esc(tx["gameId"])}",\n'
        f"datetime({ts_str}),\n"
        f'"{_esc(tx.get("sourceSystem", "pos_system"))}",\n'
        f'"{_esc(tx.get("concessionZone", "ZONE_MERCH_1"))}",\n'
        f'"{_esc(tx.get("sectionId", "S112"))}",\n'
        f'"{_esc(tx.get("category", "merchandise"))}",\n'
        f'"{_esc(tx.get("itemName", "Team Jersey"))}",\n'
        f"{int(tx.get('quantity', 1))},\n"
        f"{float(tx.get('unitPrice', 89.0))},\n"
        f"{float(tx.get('totalAmount', 71.2))},\n"
        f'"{_esc(tx.get("paymentMethod", "mobile_app"))}",\n'
        f"{str(bool(tx.get('offerRedeemed', True))).lower()},\n"
        f'"{promo_id}",\n'
        f"{float(tx.get('gameMinute', 65.0))},\n"
        f"{int(tx.get('drive', 8))},\n"
        f"{int(tx.get('quarter', 4))}\n"
        "]"
    )

    resp = requests.post(
        f"{cluster_uri}/v1/rest/mgmt",
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
        json={"db": database, "csl": csl},
        timeout=30,
    )
    resp.raise_for_status()
    log.info("Ingested POSTransaction %s to Eventhouse", tx["transactionId"])


def ingest_offer_feedback(feedback: dict, cluster_uri: str, database: str) -> None:
    """Write an OfferFeedbackEvent to Eventhouse to close the RTI feedback loop.

    The Lakehouse SQL Analytics Endpoint is read-only for Delta tables, so the
    closed-loop signal travels back through Eventhouse. The Fabric Data Agent
    queries OfferFeedbackEvent directly from Eventhouse, making the redemption
    immediately visible after this call.

    Schema matches create_kql_tables.kql exactly.
    """
    def _esc(v: object) -> str:
        return str(v).replace("\\", "\\\\").replace('"', '\\"') if v is not None else ""

    offer_ts  = str(feedback.get("offerTimestamp", ""))
    outcome_ts = str(feedback.get("outcomeTimestamp", ""))

    csl = (
        ".set-or-append OfferFeedbackEvent <|\n"
        "datatable(\n"
        "    feedbackId:string, promoId:string, fanId:string, gameId:string,\n"
        "    sourceSystem:string, offerTimestamp:datetime, outcomeTimestamp:datetime,\n"
        "    outcome:string, offerCategory:string, revenueImpact:real,\n"
        "    channel:string, gameMinute:real, drive:int, quarter:int,\n"
        "    triggerContext:string\n"
        ")[\n"
        f'"{_esc(feedback["feedbackId"])}", "{_esc(feedback["promoId"])}",\n'
        f'"{_esc(feedback["fanId"])}", "{_esc(feedback["gameId"])}",\n'
        f'"pos_system",\n'
        f"datetime({offer_ts}), datetime({outcome_ts}),\n"
        f'"redeemed", "{_esc(feedback.get("offerCategory", "merchandise"))}",\n'
        f"{float(feedback.get('revenueImpact', 0.0))},\n"
        f'"mobile_app",\n'
        f"{float(feedback.get('gameMinute', 65.0))},\n"
        f"{int(feedback.get('drive', 8))}, {int(feedback.get('quarter', 4))},\n"
        f'"{_esc(feedback.get("triggerContext", ""))}"\n'
        "]"
    )

    resp = requests.post(
        f"{cluster_uri}/v1/rest/mgmt",
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
        json={"db": database, "csl": csl},
        timeout=30,
    )
    resp.raise_for_status()
    log.info("Ingested OfferFeedbackEvent %s to Eventhouse", feedback["feedbackId"])
