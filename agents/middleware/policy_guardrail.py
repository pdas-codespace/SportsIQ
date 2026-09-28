"""Policy Guardrail — deterministic enforcement of Sports-IQ-Offer-Policy.md §3–§6.

Two entry points:

1. PolicyGuardrailMiddleware(FunctionMiddleware) — registered on the offer_generator
   agent; logs guardrail-relevant context on every tool call.

2. validate_offers(offers, game_state, fan_state) → GuardrailResult — called from
   workflow.py after offer generation; applies all 7 guardrails plus alcohol (§4.1)
   and incident override (§6) in strict policy order.

Audit trail:
    Every guardrail evaluation — pass or fail — writes a GuardrailAuditRecord via
    log.info("[GUARDRAIL_AUDIT] ...") in JSON. This lands in Application Insights on
    the same structured log path as AuditFunctionMiddleware, enabling KQL queries like:
        traces | where message startswith "[GUARDRAIL_AUDIT]"

Suppressed offers:
    Offers that fail a guardrail are NOT dropped silently. They are returned in
    GuardrailResult.suppressed_offers enriched with:
        guardrail_suppressed: True
        guardrail_reason: "<GUARDRAIL_ID>: <human-readable reason>"
        policy_ref: "§3 Guardrail N"
    The workflow emits a text_message event for each and excludes them from HITL.

Missing game_state fields:
    Guardrails that cannot be evaluated due to missing data fail-open (pass) and
    emit a log.warning. The engagement monitor SYSTEM_PROMPT is extended (see
    engagement_monitor/agent_def.py) to surface available fields. Fields requiring
    deeper Eventhouse integration (isRedZone, down, scoreDifferential) are TODOs.

Guardrail evaluation order (per §3 spec):
    G1 Red Zone → G2 Post-TD → G3 Excitement → G4 Fatigue → G5 4th-Down →
    G6 Budget Cap → G7 Pre-Halftime → Alcohol (§4.1) → Incident Override (§6)
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from agent_framework import FunctionMiddleware

from .sport_variants import SportGuardrailConfig, get_sport_config

log = logging.getLogger("sports-iq.policy-guardrail")

# Active sport config — resolved once at module load from SPORTS_IQ_SPORT env var
_SPORT: SportGuardrailConfig = get_sport_config()


@dataclass
class GuardrailAuditRecord:
    offer_id: str
    guardrail: str        # e.g. "G1_RedZone", "ALL_PASS"
    result: str           # "pass" | "suppressed"
    reason: str
    policy_ref: str       # e.g. "§3 Guardrail 1"
    evaluated_at: str     # ISO-8601 UTC
    context_snapshot: dict = field(default_factory=dict)


@dataclass
class GuardrailResult:
    clean_offers: list[dict]
    suppressed_offers: list[dict]   # enriched with guardrail_suppressed + guardrail_reason
    audit_records: list[GuardrailAuditRecord]


class PolicyGuardrailMiddleware(FunctionMiddleware):
    """MAF FunctionMiddleware registered on the offer_generator agent.

    Logs guardrail-relevant context on each tool call. The main enforcement
    logic lives in the module-level validate_offers() function, which is
    called explicitly from workflow.py after offer generation completes.
    """

    async def process(self, context, call_next) -> None:
        fn_name = context.function.name
        log.debug("[GUARDRAIL] tool_pre: %s", fn_name)
        await call_next()
        log.debug(
            "[GUARDRAIL] tool_post: %s result_len=%d",
            fn_name,
            len(str(context.result or "")),
        )


# ── Module-level validation entry point ──────────────────────────────────────

def validate_offers(
    offers: list[dict],
    game_state: dict,
    fan_state: dict,
    sport: str | None = None,
) -> GuardrailResult:
    """Evaluate all guardrails against a list of generated offers.

    Args:
        offers: Raw offer dicts from offer_generator. May be empty.
        game_state: Live game context. Keys used (all optional; missing → fail-open):
            gameExcitementIndex (float)   — G3: excitement spike threshold
            isRedZone (bool)              — G1: absolute red zone block
            lastPlayType (str | None)     — G2: touchdown suppression
            timeSinceTD (int | None)      — G2: seconds since last TD
            down (int | None)             — G5: 4th-down critical play
            scoreDifferential (int | None)— G5: close game threshold
            quarter (int | None)          — alcohol policy (§4.1)
            gameClockQ2LessThan2m30s (bool) — G7: pre-halftime premium window
            activeIncident (dict | None)  — §6: stadium incident override
        fan_state: Fan eligibility context. Keys used:
            loyaltyTier (str)             — G4, G6, G7 tier-specific rules
            minutesSinceLastOffer (int | None) — G4: fatigue gap check
            totalOffersThisGame (int)     — G6: budget cap offer count
            totalOfferValueThisGame (float) — G6: budget cap value

        sport: Override the active sport (default: reads SPORTS_IQ_SPORT env var).
            Useful in tests to isolate sport-specific guardrail thresholds.

    Returns:
        GuardrailResult with clean_offers (for HITL) and suppressed_offers (audit
        trail only — never forwarded to human review). Every evaluation, pass or
        fail, produces a GuardrailAuditRecord.
    """
    sport_cfg = get_sport_config(sport) if sport is not None else _SPORT
    clean: list[dict] = []
    suppressed: list[dict] = []
    audit: list[GuardrailAuditRecord] = []

    for offer in offers:
        offer_id = offer.get("id", "unknown")
        hit = _first_firing_guardrail(offer, game_state, fan_state, offers, sport_cfg)
        now = datetime.now(timezone.utc).isoformat()
        snapshot = {
            "game_state": _safe_snapshot(game_state),
            "fan_state": _safe_snapshot(fan_state),
        }

        if hit:
            record = GuardrailAuditRecord(
                offer_id=offer_id,
                guardrail=hit["guardrail"],
                result="suppressed",
                reason=hit["reason"],
                policy_ref=hit["policy_ref"],
                evaluated_at=now,
                context_snapshot=snapshot,
            )
            audit.append(record)
            log.info("[GUARDRAIL_AUDIT] %s", json.dumps(asdict(record), default=str))
            suppressed.append({
                **offer,
                "guardrail_suppressed": True,
                "guardrail_reason": f"{hit['guardrail']}: {hit['reason']}",
                "policy_ref": hit["policy_ref"],
            })
        else:
            record = GuardrailAuditRecord(
                offer_id=offer_id,
                guardrail="ALL_PASS",
                result="pass",
                reason="All guardrails passed",
                policy_ref="§3",
                evaluated_at=now,
                context_snapshot=snapshot,
            )
            audit.append(record)
            log.info("[GUARDRAIL_AUDIT] %s", json.dumps(asdict(record), default=str))
            clean.append(offer)

    return GuardrailResult(
        clean_offers=clean,
        suppressed_offers=suppressed,
        audit_records=audit,
    )


# ── Guardrail dispatcher ──────────────────────────────────────────────────────

def _first_firing_guardrail(
    offer: dict,
    gs: dict,
    fs: dict,
    all_offers: list[dict],
    cfg: SportGuardrailConfig,
) -> dict | None:
    """Return the first guardrail that fires (in policy order), or None."""
    checks = [
        _g1_scoring_zone(gs, cfg),
        _g2_post_score(gs, cfg),
        _g3_excitement(gs, cfg),
        _g4_fatigue(fs, cfg),
        _g5_critical_play(gs, cfg),
        _g6_budget_cap(fs, all_offers, cfg),
        _g7_premium_window(gs, fs, cfg),
        _alcohol_policy(offer, gs, cfg),
        _incident_override(offer, gs),
        *_extra_suppressions(gs, cfg),
    ]
    return next((c for c in checks if c is not None), None)


# ── Individual guardrail implementations ─────────────────────────────────────

def _g1_scoring_zone(gs: dict, cfg: SportGuardrailConfig) -> dict | None:
    """§3 Guardrail 1 — Scoring zone suppression (sport-specific, absolute)."""
    fld = cfg.scoring_zone_field
    if fld not in gs or gs[fld] is None:
        log.warning("[GUARDRAIL] G1_ScoringZone: %s missing from game_state — skipping check", fld)
        return None
    if gs[fld]:
        return {
            "guardrail": "G1_ScoringZone",
            "reason": f"{fld}=true — {cfg.scoring_zone_label} — all offers blocked",
            "policy_ref": "§3 Guardrail 1",
        }
    return None


def _g2_post_score(gs: dict, cfg: SportGuardrailConfig) -> dict | None:
    """§3 Guardrail 2 — Post-score celebration window (sport-specific duration)."""
    if "lastPlayType" not in gs or "timeSinceScore" not in gs:
        log.warning("[GUARDRAIL] G2_PostScore: lastPlayType/timeSinceScore missing — skipping check")
        return None
    window = cfg.celebration_window_seconds
    expected = cfg.score_play_type
    if gs.get("lastPlayType") == expected and (gs.get("timeSinceScore") or 999) < window:
        return {
            "guardrail": "G2_PostScore",
            "reason": f"lastPlayType={expected} AND timeSinceScore={gs['timeSinceScore']}s < {window}s",
            "policy_ref": "§3 Guardrail 2",
        }
    return None


def _g3_excitement(gs: dict, cfg: SportGuardrailConfig) -> dict | None:
    """§3 Guardrail 3 — Game Excitement Suppression (sport-specific threshold)."""
    gei = gs.get("gameExcitementIndex")
    if gei is None:
        log.warning("[GUARDRAIL] G3_Excitement: gameExcitementIndex missing — skipping check")
        return None
    threshold = cfg.excitement_threshold
    if gei > threshold:
        return {
            "guardrail": "G3_ExcitementSpike",
            "reason": f"gameExcitementIndex={gei:.3f} > {threshold}",
            "policy_ref": "§3 Guardrail 3",
        }
    return None


def _g4_fatigue(fs: dict, cfg: SportGuardrailConfig) -> dict | None:
    """§3 Guardrail 4 — Offer Fatigue (sport- and tier-specific minimum gap)."""
    tier = fs.get("loyaltyTier", "Bronze")
    gap = cfg.fatigue_gap.get(tier, 60)
    minutes_since = fs.get("minutesSinceLastOffer")
    if minutes_since is None:
        log.debug("[GUARDRAIL] G4_Fatigue: minutesSinceLastOffer not available — skipping check")
        return None
    if minutes_since < gap:
        return {
            "guardrail": "G4_OfferFatigue",
            "reason": f"minutesSinceLastOffer={minutes_since} < {gap}min (tier={tier})",
            "policy_ref": "§3 Guardrail 4",
        }
    return None


def _g5_critical_play(gs: dict, cfg: SportGuardrailConfig) -> dict | None:
    """§3 Guardrail 5 — Critical play suppression (sport-specific trigger)."""
    fld = cfg.critical_play_field
    if fld not in gs or "scoreDifferential" not in gs:
        log.warning("[GUARDRAIL] G5_CriticalPlay: %s/scoreDifferential missing — skipping check", fld)
        return None
    val = cfg.critical_play_value
    margin = cfg.critical_play_score_margin
    field_val = gs.get(fld)
    if cfg.critical_play_comparison == "==":
        match = field_val == val
    else:  # "<="
        match = field_val is not None and field_val <= val
    if match and abs(gs.get("scoreDifferential") or 99) <= margin:
        return {
            "guardrail": "G5_CriticalPlay",
            "reason": (
                f"{cfg.critical_play_label}: {fld}={field_val} "
                f"AND |scoreDifferential|={abs(gs.get('scoreDifferential') or 0)} ≤ {margin}"
            ),
            "policy_ref": "§3 Guardrail 5",
        }
    return None


def _g6_budget_cap(fs: dict, all_offers: list[dict], cfg: SportGuardrailConfig) -> dict | None:
    """§3 Guardrail 6 — Per-Fan Budget Cap (sport- and tier-specific)."""
    tier = fs.get("loyaltyTier", "Bronze")
    cap = cfg.budget_cap.get(tier, cfg.budget_cap["Bronze"])
    total_offers = (fs.get("totalOffersThisGame") or 0) + len(all_offers)
    total_value = fs.get("totalOfferValueThisGame") or 0.0
    if total_offers > cap["max_offers"] or total_value > cap["max_value"]:
        return {
            "guardrail": "G6_BudgetCap",
            "reason": (
                f"tier={tier}: totalOffers={total_offers} (max={cap['max_offers']}), "
                f"totalValue=${total_value:.2f} (max=${cap['max_value']:.2f})"
            ),
            "policy_ref": "§3 Guardrail 6",
        }
    return None


def _g7_premium_window(gs: dict, fs: dict, cfg: SportGuardrailConfig) -> dict | None:
    """§3 Guardrail 7 — Premium window suppression (sport-specific)."""
    fld = cfg.premium_window_field
    if fld not in gs or gs[fld] is None:
        log.debug("[GUARDRAIL] G7_PremiumWindow: %s missing — skipping check", fld)
        return None
    tier = fs.get("loyaltyTier", "Bronze")
    if gs[fld] and tier != "Platinum":
        return {
            "guardrail": "G7_PremiumWindow",
            "reason": f"{cfg.premium_window_label} AND loyaltyTier={tier} (Platinum-only window)",
            "policy_ref": "§3 Guardrail 7",
        }
    return None


def _alcohol_policy(offer: dict, gs: dict, cfg: SportGuardrailConfig) -> dict | None:
    """§4.1 — No alcohol offers after the sport-specific cutoff period."""
    title_lower = (offer.get("title") or "").lower()
    desc_lower = (offer.get("description") or "").lower()
    is_alcohol = any(
        kw in title_lower or kw in desc_lower
        for kw in ("alcohol", "beer", "wine", "spirits", "cocktail", "draft pint", "brew")
    )
    if not is_alcohol:
        return None
    quarter = gs.get("quarter")
    if quarter is None:
        log.debug("[GUARDRAIL] AlcoholPolicy: quarter missing — skipping check")
        return None
    cutoff = cfg.alcohol_cutoff_quarter
    if quarter >= cutoff:
        return {
            "guardrail": "AlcoholPolicy",
            "reason": f"Alcohol offer blocked (current {cfg.periods_name}={quarter}, cutoff={cutoff})",
            "policy_ref": "§4.1 Alcohol Policy",
        }
    return None


def _incident_override(offer: dict, gs: dict) -> dict | None:
    """§6 — Stadium Incident Override (absolute block for restricted categories)."""
    incident = gs.get("activeIncident")
    if not incident:
        return None
    restricted: list[str] = incident.get("restrictedOfferCategories", [])
    offer_cat = offer.get("category", "")
    if offer_cat in restricted:
        return {
            "guardrail": "IncidentOverride",
            "reason": (
                f"Stadium incident active — offer category '{offer_cat}' "
                f"in restrictedCategories={restricted}"
            ),
            "policy_ref": "§6 Stadium Incident Override",
        }
    return None


def _extra_suppressions(gs: dict, cfg: SportGuardrailConfig) -> list[dict | None]:
    """Evaluate sport-specific extra suppression rules from config."""
    results: list[dict | None] = []
    for rule in cfg.extra_suppressions:
        fld = rule["field"]
        if fld not in gs or gs[fld] is None:
            log.debug("[GUARDRAIL] %s: %s missing — skipping check", rule["id"], fld)
            results.append(None)
            continue
        if gs[fld]:
            results.append({
                "guardrail": rule["id"],
                "reason": rule["label"],
                "policy_ref": rule.get("policy_ref", "§3 Sport-specific"),
            })
        else:
            results.append(None)
    return results


def _safe_snapshot(d: dict) -> dict:
    """Truncate long string values for log-safe context snapshots."""
    return {k: (str(v)[:120] if isinstance(v, str) else v) for k, v in d.items()}
