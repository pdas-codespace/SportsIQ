"""Lakehouse SQL client — queries fan_profile, stadium_incident, merchandise_inventory via pyodbc.

stadium_incident columns (when table exists):
  incidentId, gameId, reportedAt, affectedSections, incidentType, severity,
  status, restrictedOfferCategories, resolvedAt, notes
"""
from __future__ import annotations
import pyodbc
import struct
from azure.identity import DefaultAzureCredential

_credential = DefaultAzureCredential()
_SQL_SCOPE = "https://database.windows.net/.default"


def _get_connection(sql_endpoint: str, database: str) -> pyodbc.Connection:
    token_bytes = _credential.get_token(_SQL_SCOPE).token.encode("utf-16-le")
    token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
    conn_str = (
        f"Driver={{ODBC Driver 18 for SQL Server}};"
        f"Server={sql_endpoint},1433;"
        f"Database={database};"
        "Encrypt=yes;TrustServerCertificate=no;"
    )
    conn = pyodbc.connect(conn_str, attrs_before={1256: token_struct})
    return conn


def _esc(value: str) -> str:
    """Escape a string for safe T-SQL interpolation (single-quote doubling)."""
    return value.replace("'", "''")


def query(sql: str, sql_endpoint: str, database: str, schema: str = "dbo") -> list[dict]:
    conn = _get_connection(sql_endpoint, database)
    cursor = conn.cursor()
    cursor.execute(sql)
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_fan_profile(fan_id: str, sql_endpoint: str, database: str, schema: str = "dbo") -> dict | None:
    rows = query(
        f"SELECT fanId, loyaltyTier, preferredSectionId, avgSpendPerGame, avgConcessionSpend, "
        f"avgMerchandiseSpend, offerFatigueGapMinutes, baseEngagementScore, churnRiskScore "
        f"FROM {schema}.fan_profile WHERE fanId = '{_esc(fan_id)}'",
        sql_endpoint, database, schema,
    )
    return rows[0] if rows else None


def get_offer_fatigue_status(fan_id: str, sql_endpoint: str, database: str, schema: str = "dbo") -> dict:
    rows = query(
        f"""
        SELECT fp.fanId, fp.loyaltyTier, fp.offerFatigueGapMinutes AS requiredGapMins,
               MAX(ph.lastOfferTimestamp) AS lastOfferTs,
               DATEDIFF(minute, MAX(ph.lastOfferTimestamp), GETDATE()) AS minsSinceLastOffer
        FROM {schema}.fan_profile fp
        LEFT JOIN {schema}.promotion_history ph ON fp.fanId = ph.fanId
        WHERE fp.fanId = '{_esc(fan_id)}'
        GROUP BY fp.fanId, fp.loyaltyTier, fp.offerFatigueGapMinutes
        """,
        sql_endpoint, database, schema,
    )
    if not rows:
        return {"eligible": False, "reason": "fan not found"}
    r = rows[0]
    mins = r.get("minsSinceLastOffer") or 0
    eligible = mins >= r["requiredGapMins"]
    return {
        "fanId": r["fanId"],
        "loyaltyTier": r["loyaltyTier"],
        "requiredGapMins": r["requiredGapMins"],
        "minsSinceLastOffer": mins,
        "eligible": eligible,
    }


def get_active_incidents(section_id: str, sql_endpoint: str, database: str, schema: str = "dbo") -> list[dict]:
    # Normalize: accept both "S112" and "112"
    section_num = section_id.lstrip("S").lstrip("s")
    try:
        rows = query(
            f"""
            SELECT incidentId, incidentType, affectedSections, severity,
                   restrictedOfferCategories, description
            FROM {schema}.stadium_incident
            WHERE status = 'active'
              AND affectedSections LIKE '%{section_num}%'
            """,
            sql_endpoint, database, schema,
        )
        return rows
    except Exception as exc:
        raise RuntimeError(
            "Unable to query stadium_incident. Run the Fabric bootstrap and verify "
            "the managed identity can read the Lakehouse SQL endpoint."
        ) from exc


def get_merch_inventory(stadium_id: str, sql_endpoint: str, database: str, schema: str = "dbo") -> list[dict]:
    return query(
        f"""
        SELECT itemId, playerName, playerNumber, teamName, category, price, stockLevel,
               popularityRank, nearestSectionIds, currentlyOnPromo, standLocation
        FROM {schema}.merchandise_inventory
        WHERE stadiumId = '{stadium_id}' AND stockLevel > 0
        ORDER BY popularityRank ASC
        """,
        sql_endpoint, database, schema,
    )


import hashlib

_FIRST_NAMES = [
    "Marcus", "DeShawn", "Jaylen", "Malik", "Tre", "Jordan", "Darius",
    "Elijah", "Isaiah", "Kameron", "Tyrese", "Jamal", "Andre", "Devon",
    "Jalen", "Corey", "Rasheed", "Brandon", "Derrick", "Kwame", "Chris",
    "Michael", "Lamar", "Terrence", "Xavier", "Desmond", "Reggie", "Dwayne",
    "Kevin", "Donovan", "Alonzo", "Byron", "Calvin", "Ernest", "Floyd",
    "Gerald", "Harold", "Irving", "Jerome", "Kenneth", "Leonard", "Maurice",
    "Nathan", "Oliver", "Percy", "Quincy", "Roland", "Stanley", "Tyrone",
    "Ulysses", "Victor", "Walter", "Yolanda", "Zara", "Aisha", "Brianna",
    "Camille", "Danielle", "Ebony", "Faith", "Gabrielle", "Hailey", "Imani",
    "Jasmine", "Keisha", "Latoya", "Monique", "Naomi", "Olivia", "Priya",
    "Quinn", "Renee", "Simone", "Tasha", "Vanessa", "Whitney",
]

_LAST_NAMES = [
    "Johnson", "Williams", "Brown", "Davis", "Miller", "Wilson", "Moore",
    "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin",
    "Thompson", "Garcia", "Martinez", "Robinson", "Clark", "Rodriguez",
    "Lewis", "Lee", "Walker", "Hall", "Allen", "Young", "Hernandez",
    "King", "Wright", "Lopez", "Hill", "Scott", "Green", "Adams", "Baker",
    "Gonzalez", "Nelson", "Carter", "Mitchell", "Perez", "Roberts", "Turner",
    "Phillips", "Campbell", "Parker", "Evans", "Edwards", "Collins", "Stewart",
    "Sanchez", "Morris", "Rogers", "Reed", "Cook", "Morgan", "Bell", "Murphy",
    "Bailey", "Rivera", "Cooper", "Richardson", "Cox", "Howard", "Ward",
    "Torres", "Peterson", "Gray", "Ramirez", "James", "Watson", "Brooks",
    "Kelly", "Sanders", "Price", "Bennett", "Wood", "Barnes", "Ross",
]


def _fan_name_from_id(fan_id: str) -> str:
    """Deterministically map a fanId to a realistic full name using MD5 hash."""
    digest = hashlib.md5(fan_id.encode()).digest()
    first = _FIRST_NAMES[digest[0] % len(_FIRST_NAMES)]
    last = _LAST_NAMES[digest[1] % len(_LAST_NAMES)]
    return f"{first} {last}"


def _fans_with_fatigue(rows: list[dict]) -> list[dict]:
    """Normalise a raw fan_profile + promotion_history result into the FanProfile shape."""
    out = []
    for r in rows:
        mins = r.get("minsSinceLastOffer")
        gap = r.get("offerFatigueGapMinutes") or 0
        fatigued = (mins is not None) and (mins < gap)
        days_ago = round(mins / 1440) if mins is not None else -1
        fan_id = r["fanId"]
        out.append({
            "fanId": fan_id,
            "fanName": r.get("fanName") or _fan_name_from_id(fan_id),
            "loyaltyTier": r["loyaltyTier"],
            "preferredSectionId": r.get("preferredSectionId") or "",
            "baseEngagementScore": float(r.get("baseEngagementScore") or 0),
            "lastOfferDaysAgo": days_ago,
            "offerFatigued": fatigued,
        })
    return out


def _query_with_fan_name_fallback(
    sql_with_name: str, sql_without_name: str,
    sql_endpoint: str, database: str, schema: str
) -> list[dict]:
    """Try query with fanName; if column missing, retry without it."""
    try:
        return query(sql_with_name, sql_endpoint, database, schema)
    except Exception as exc:
        if "fanName" in str(exc) or "207" in str(exc):  # 207 = invalid column name
            return query(sql_without_name, sql_endpoint, database, schema)
        raise


def get_fan_profiles_for_ids(fan_ids: list[str], sql_endpoint: str, database: str, schema: str = "dbo") -> list[dict]:
    """Return profiles for a specific set of fanIds with offer-fatigue status."""
    if not fan_ids:
        return []
    id_list = ", ".join(f"'{_esc(f)}'" for f in fan_ids)
    rows = _query_with_fan_name_fallback(
        f"""
        SELECT fp.fanId, fp.fanName, fp.loyaltyTier, fp.preferredSectionId,
               fp.baseEngagementScore, fp.offerFatigueGapMinutes, fp.churnRiskScore,
               DATEDIFF(minute, MAX(ph.lastOfferTimestamp), GETDATE()) AS minsSinceLastOffer
        FROM {schema}.fan_profile fp
        LEFT JOIN {schema}.promotion_history ph ON fp.fanId = ph.fanId
        WHERE fp.fanId IN ({id_list})
        GROUP BY fp.fanId, fp.fanName, fp.loyaltyTier, fp.preferredSectionId,
                 fp.baseEngagementScore, fp.offerFatigueGapMinutes, fp.churnRiskScore
        """,
        f"""
        SELECT fp.fanId, fp.loyaltyTier, fp.preferredSectionId,
               fp.baseEngagementScore, fp.offerFatigueGapMinutes, fp.churnRiskScore,
               DATEDIFF(minute, MAX(ph.lastOfferTimestamp), GETDATE()) AS minsSinceLastOffer
        FROM {schema}.fan_profile fp
        LEFT JOIN {schema}.promotion_history ph ON fp.fanId = ph.fanId
        WHERE fp.fanId IN ({id_list})
        GROUP BY fp.fanId, fp.loyaltyTier, fp.preferredSectionId,
                 fp.baseEngagementScore, fp.offerFatigueGapMinutes, fp.churnRiskScore
        """,
        sql_endpoint, database, schema,
    )
    return _fans_with_fatigue([{**r, "churnRiskScore": r.get("churnRiskScore", 0)} for r in rows])


def get_fans_by_tier(tier: str, sql_endpoint: str, database: str, schema: str = "dbo") -> list[dict]:
    """Return all fans of a loyalty tier with offer-fatigue status from Lakehouse SQL."""
    rows = _query_with_fan_name_fallback(
        f"""
        SELECT fp.fanId, fp.fanName, fp.loyaltyTier, fp.preferredSectionId,
               fp.baseEngagementScore, fp.offerFatigueGapMinutes,
               DATEDIFF(minute, MAX(ph.lastOfferTimestamp), GETDATE()) AS minsSinceLastOffer
        FROM {schema}.fan_profile fp
        LEFT JOIN {schema}.promotion_history ph ON fp.fanId = ph.fanId
        WHERE fp.loyaltyTier = '{tier}'
        GROUP BY fp.fanId, fp.fanName, fp.loyaltyTier, fp.preferredSectionId,
                 fp.baseEngagementScore, fp.offerFatigueGapMinutes
        ORDER BY fp.baseEngagementScore ASC
        """,
        f"""
        SELECT fp.fanId, fp.loyaltyTier, fp.preferredSectionId,
               fp.baseEngagementScore, fp.offerFatigueGapMinutes,
               DATEDIFF(minute, MAX(ph.lastOfferTimestamp), GETDATE()) AS minsSinceLastOffer
        FROM {schema}.fan_profile fp
        LEFT JOIN {schema}.promotion_history ph ON fp.fanId = ph.fanId
        WHERE fp.loyaltyTier = '{tier}'
        GROUP BY fp.fanId, fp.loyaltyTier, fp.preferredSectionId,
                 fp.baseEngagementScore, fp.offerFatigueGapMinutes
        ORDER BY fp.baseEngagementScore ASC
        """,
        sql_endpoint, database, schema,
    )
    return _fans_with_fatigue(rows)


def get_fans_by_sections(section_ids: list[str], sql_endpoint: str, database: str, schema: str = "dbo") -> list[dict]:
    """Return all fans whose preferredSectionId is in section_ids with offer-fatigue status."""
    if not section_ids:
        return []
    placeholders = ", ".join(f"'{s}'" for s in section_ids)
    rows = _query_with_fan_name_fallback(
        f"""
        SELECT fp.fanId, fp.fanName, fp.loyaltyTier, fp.preferredSectionId,
               fp.baseEngagementScore, fp.offerFatigueGapMinutes,
               DATEDIFF(minute, MAX(ph.lastOfferTimestamp), GETDATE()) AS minsSinceLastOffer
        FROM {schema}.fan_profile fp
        LEFT JOIN {schema}.promotion_history ph ON fp.fanId = ph.fanId
        WHERE fp.preferredSectionId IN ({placeholders})
        GROUP BY fp.fanId, fp.fanName, fp.loyaltyTier, fp.preferredSectionId,
                 fp.baseEngagementScore, fp.offerFatigueGapMinutes
        ORDER BY fp.preferredSectionId, fp.baseEngagementScore ASC
        """,
        f"""
        SELECT fp.fanId, fp.loyaltyTier, fp.preferredSectionId,
               fp.baseEngagementScore, fp.offerFatigueGapMinutes,
               DATEDIFF(minute, MAX(ph.lastOfferTimestamp), GETDATE()) AS minsSinceLastOffer
        FROM {schema}.fan_profile fp
        LEFT JOIN {schema}.promotion_history ph ON fp.fanId = ph.fanId
        WHERE fp.preferredSectionId IN ({placeholders})
        GROUP BY fp.fanId, fp.loyaltyTier, fp.preferredSectionId,
                 fp.baseEngagementScore, fp.offerFatigueGapMinutes
        ORDER BY fp.preferredSectionId, fp.baseEngagementScore ASC
        """,
        sql_endpoint, database, schema,
    )
    return _fans_with_fatigue(rows)


def get_fan_detail(fan_id: str, sql_endpoint: str, database: str, schema: str = "dbo") -> dict | None:
    """Return full fan profile + last 5 offers for the detail panel."""
    profiles = _query_with_fan_name_fallback(
        f"""
        SELECT fanId, fanName, loyaltyTier, preferredSectionId,
               avgSpendPerGame, avgConcessionSpend, avgMerchandiseSpend,
               baseEngagementScore, churnRiskScore, offerFatigueGapMinutes
        FROM {schema}.fan_profile
        WHERE fanId = '{_esc(fan_id)}'
        """,
        f"""
        SELECT fanId, loyaltyTier, preferredSectionId,
               avgSpendPerGame, avgConcessionSpend, avgMerchandiseSpend,
               baseEngagementScore, churnRiskScore, offerFatigueGapMinutes
        FROM {schema}.fan_profile
        WHERE fanId = '{_esc(fan_id)}'
        """,
        sql_endpoint, database, schema,
    )
    if not profiles:
        return None
    profile = profiles[0]
    profile["fanName"] = profile.get("fanName") or _fan_name_from_id(fan_id)

    recent_offers = query(
        f"""
        SELECT TOP 5
               promoId, offerTimestamp, offerCategory, offerType,
               offerValue, channel, triggerContext, outcome, revenueImpact,
               promoResponseRate
        FROM {schema}.promotion_history
        WHERE fanId = '{_esc(fan_id)}'
        ORDER BY offerTimestamp DESC
        """,
        sql_endpoint, database, schema,
    )
    for o in recent_offers:
        o["offerValue"] = float(o["offerValue"] or 0)
        o["revenueImpact"] = float(o["revenueImpact"] or 0)
        o["promoResponseRate"] = float(o["promoResponseRate"] or 0)
        if hasattr(o.get("offerTimestamp"), "isoformat"):
            o["offerTimestamp"] = o["offerTimestamp"].isoformat()

    for key in ("avgSpendPerGame", "avgConcessionSpend", "avgMerchandiseSpend",
                "baseEngagementScore", "churnRiskScore"):
        profile[key] = float(profile.get(key) or 0)
    profile["recentOffers"] = recent_offers
    return profile


def log_offer_decision(
    offer_id: str, fan_id: str, game_id: str, decision: str, reason: str,
    sql_endpoint: str, database: str, schema: str = "dbo",
) -> None:
    """Log an offer approval/rejection to offer_decision_log.

    IMPORTANT: sql_endpoint must be a Fabric Warehouse endpoint (WAREHOUSE_SQL_ENDPOINT).
    The Lakehouse SQL Analytics Endpoint is read-only — DML will fail with error 24559.
    """
    query(
        f"""
        INSERT INTO {schema}.offer_decision_log
            (offerId, fanId, gameId, decision, decisionReason, decidedAt)
        VALUES
            ('{_esc(offer_id)}', '{_esc(fan_id)}', '{_esc(game_id)}', '{_esc(decision)}',
             '{_esc(reason)}', GETDATE())
        """,
        sql_endpoint, database, schema,
    )


def record_pos_transaction_lakehouse(
    transaction_id: str,
    fan_id: str,
    game_id: str,
    offer_category: str,
    item_description: str,
    item_price: float,
    discount_applied: float,
    amount_paid: float,
    linked_promo_id: str,
    sql_endpoint: str,
    database: str,
    schema: str = "dbo",
) -> None:
    """Insert a redeemed POS transaction into the Warehouse pos_transaction table.

    IMPORTANT: sql_endpoint must be a Fabric Warehouse endpoint (WAREHOUSE_SQL_ENDPOINT).
    The Lakehouse SQL Analytics Endpoint is read-only — DML will fail with error 24559.

    Called after a successful Stadium POS redemption so that the Fabric Data Agent
    can answer questions like "what did fan X buy / pay?" by joining
    pos_transaction.linkedPromoId → promotion_history.promoId.
    """
    query(
        f"""
        INSERT INTO {schema}.pos_transaction
            (transactionId, fanId, gameId, transactionTimestamp,
             offerCategory, subCategory, itemDescription, itemPrice,
             discountApplied, amountPaid, linkedPromoId)
        VALUES
            ('{_esc(transaction_id)}', '{_esc(fan_id)}', '{_esc(game_id)}', GETDATE(),
             '{_esc(offer_category)}', '{_esc(offer_category)}', '{_esc(item_description)}', {item_price:.2f},
             {discount_applied:.2f}, {amount_paid:.2f}, '{_esc(linked_promo_id)}')
        """,
        sql_endpoint, database, schema,
    )


def record_offer_redemption(
    fan_id: str,
    game_id: str,
    promo_id: str,
    offer_category: str,
    offer_type: str,
    offer_value: float,
    revenue_impact: float,
    trigger_context: str,
    sql_endpoint: str,
    database: str,
    schema: str = "dbo",
) -> None:
    """Insert a redeemed offer into promotion_history and update the fan's lastOfferTimestamp.

    IMPORTANT: sql_endpoint must be a Fabric Warehouse endpoint (WAREHOUSE_SQL_ENDPOINT).
    The Lakehouse SQL Analytics Endpoint is read-only — DML will fail with error 24559.

    Called after a successful Stadium POS redemption to close the feedback loop.
    The inserted row immediately becomes visible to the Fabric Data Agent via the
    Warehouse SQL endpoint.
    """
    query(
        f"""
        INSERT INTO {schema}.promotion_history
            (promoId, fanId, gameId, offerTimestamp, offerCategory, offerType,
             offerValue, channel, triggerContext, outcome, revenueImpact,
             lastOfferTimestamp, promoResponseRate)
        VALUES
            ('{_esc(promo_id)}', '{_esc(fan_id)}', '{_esc(game_id)}', GETDATE(),
             '{_esc(offer_category)}', '{_esc(offer_type)}', {offer_value:.2f},
             'mobile_app', '{_esc(trigger_context)}', 'redeemed', {revenue_impact:.2f},
             GETDATE(), 1.0)
        """,
        sql_endpoint, database, schema,
    )
