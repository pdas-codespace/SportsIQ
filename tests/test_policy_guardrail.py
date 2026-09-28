"""Tests for agents/middleware/policy_guardrail.py

Covers every guardrail in evaluation order plus structural contracts:
  - Each guardrail fires on its exact condition
  - Each guardrail passes when its condition is NOT met
  - Fail-open: missing game_state keys do NOT suppress
  - First-firing-wins: G1 fires before G3 when both are active
  - GuardrailResult structure: clean_offers / suppressed_offers / audit_records
  - Audit records are written for every offer regardless of outcome
  - Multiple independent offers are each evaluated independently
  - PolicyGuardrailMiddleware is importable from the middleware package
"""
import copy
import pytest

from agents.middleware.policy_guardrail import (
    GuardrailAuditRecord,
    GuardrailResult,
    PolicyGuardrailMiddleware,
    validate_offers,
)
from agents.middleware import PolicyGuardrailMiddleware as PackageExport  # re-export check


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def offer():
    """A single merchandise offer that passes all guardrails by default."""
    return {
        "id": "offer_001",
        "title": "Team Jersey Deal",
        "description": "20% off official jerseys at Section 112 stand",
        "category": "merchandise",
    }


@pytest.fixture
def food_offer():
    return {
        "id": "offer_002",
        "title": "Combo Meal Deal",
        "description": "Buy any combo, get a free drink",
        "category": "food_beverage",
    }


@pytest.fixture
def alcohol_offer():
    return {
        "id": "offer_003",
        "title": "Draft Beer Special",
        "description": "Half-price draft beer at Section 108 bar",
        "category": "food_beverage",
    }


@pytest.fixture
def clean_game_state():
    """Game state that passes every guardrail."""
    return {
        "gameExcitementIndex": 0.50,
        "isRedZone": False,
        "lastPlayType": "pass_complete",
            "timeSinceScore": 180,
        "down": 1,
        "scoreDifferential": 14,
        "quarter": 2,
        "gameClockQ2LessThan2m30s": False,
        "activeIncident": None,
    }


@pytest.fixture
def clean_fan_state():
    """Fan state that passes every guardrail (Gold tier, well within all caps)."""
    return {
        "loyaltyTier": "Gold",
        "minutesSinceLastOffer": 45,
        "totalOffersThisGame": 0,
        "totalOfferValueThisGame": 0.0,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _suppressed_guardrail(result: GuardrailResult) -> str | None:
    """Return the guardrail ID of the first suppressed offer, or None."""
    if result.suppressed_offers:
        return result.suppressed_offers[0].get("guardrail_reason", "").split(":")[0]
    return None


# ── Package export ─────────────────────────────────────────────────────────────

def test_package_exports_middleware():
    assert PolicyGuardrailMiddleware is PackageExport


# ── ALL_PASS baseline ─────────────────────────────────────────────────────────

def test_all_pass(offer, clean_game_state, clean_fan_state):
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1
    assert len(result.suppressed_offers) == 0
    assert result.audit_records[0].result == "pass"
    assert result.audit_records[0].guardrail == "ALL_PASS"


# ── G1 — Scoring Zone (sport-specific field) ──────────────────────────────────

def test_g1_suppresses_when_in_red_zone(offer, clean_game_state, clean_fan_state):
    clean_game_state["isRedZone"] = True
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 0
    assert result.suppressed_offers[0]["guardrail_suppressed"] is True
    assert "G1_ScoringZone" in result.suppressed_offers[0]["guardrail_reason"]
    assert result.suppressed_offers[0]["policy_ref"] == "§3 Guardrail 1"


def test_g1_passes_when_not_in_red_zone(offer, clean_game_state, clean_fan_state):
    clean_game_state["isRedZone"] = False
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


def test_g1_fail_open_when_key_missing(offer, clean_fan_state):
    gs = {"gameExcitementIndex": 0.5, "quarter": 2}  # no isRedZone key
    result = validate_offers([offer], gs, clean_fan_state, sport="football")
    # Should NOT suppress — fail-open
    assert len(result.clean_offers) == 1


# ── G2 — Post-Score Celebration Window ───────────────────────────────────────

def test_g2_suppresses_within_60s_of_touchdown(offer, clean_game_state, clean_fan_state):
    clean_game_state["lastPlayType"] = "touchdown"
    clean_game_state["timeSinceScore"] = 30
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert "G2_PostScore" in result.suppressed_offers[0]["guardrail_reason"]


def test_g2_passes_after_60s(offer, clean_game_state, clean_fan_state):
    clean_game_state["lastPlayType"] = "touchdown"
    clean_game_state["timeSinceScore"] = 61
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


def test_g2_passes_on_non_touchdown_play(offer, clean_game_state, clean_fan_state):
    clean_game_state["lastPlayType"] = "run"
    clean_game_state["timeSinceScore"] = 10  # recent, but not a touchdown play type
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


def test_g2_fail_open_when_keys_missing(offer, clean_fan_state):
    gs = {"gameExcitementIndex": 0.5, "isRedZone": False}  # no lastPlayType / timeSinceScore
    result = validate_offers([offer], gs, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


# ── G3 — Game Excitement ──────────────────────────────────────────────────────

def test_g3_suppresses_above_threshold(offer, clean_game_state, clean_fan_state):
    clean_game_state["gameExcitementIndex"] = 0.85
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert "G3_ExcitementSpike" in result.suppressed_offers[0]["guardrail_reason"]


def test_g3_passes_at_threshold_boundary(offer, clean_game_state, clean_fan_state):
    clean_game_state["gameExcitementIndex"] = 0.78  # exactly 0.78 — not above
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


def test_g3_passes_below_threshold(offer, clean_game_state, clean_fan_state):
    clean_game_state["gameExcitementIndex"] = 0.60
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


def test_g3_fail_open_when_missing(offer, clean_fan_state):
    gs = {"isRedZone": False, "quarter": 2}
    result = validate_offers([offer], gs, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


# ── G4 — Offer Fatigue ────────────────────────────────────────────────────────

@pytest.mark.parametrize("tier,gap,minutes_since,expect_suppressed", [
    ("Bronze",   60, 59, True),
    ("Bronze",   60, 60, False),
    ("Silver",   45, 44, True),
    ("Silver",   45, 45, False),
    ("Gold",     30, 29, True),
    ("Gold",     30, 30, False),
    ("Platinum", 20, 19, True),
    ("Platinum", 20, 20, False),
])
def test_g4_tier_specific_gaps(offer, clean_game_state, tier, gap, minutes_since, expect_suppressed):
    fan_state = {
        "loyaltyTier": tier,
        "minutesSinceLastOffer": minutes_since,
        "totalOffersThisGame": 0,
        "totalOfferValueThisGame": 0.0,
    }
    result = validate_offers([offer], clean_game_state, fan_state, sport="football")
    if expect_suppressed:
        assert "G4_OfferFatigue" in result.suppressed_offers[0]["guardrail_reason"], \
            f"{tier} at {minutes_since}min should be suppressed (gap={gap})"
    else:
        assert len(result.clean_offers) == 1, \
            f"{tier} at {minutes_since}min should pass (gap={gap})"


def test_g4_fail_open_when_minutes_missing(offer, clean_game_state):
    fan_state = {"loyaltyTier": "Gold"}  # no minutesSinceLastOffer
    result = validate_offers([offer], clean_game_state, fan_state, sport="football")
    assert len(result.clean_offers) == 1


# ── G5 — Critical Play ────────────────────────────────────────────────────────

def test_g5_suppresses_on_4th_and_close(offer, clean_game_state, clean_fan_state):
    clean_game_state["down"] = 4
    clean_game_state["scoreDifferential"] = 3
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert "G5_CriticalPlay" in result.suppressed_offers[0]["guardrail_reason"]


def test_g5_suppresses_when_score_diff_exactly_7(offer, clean_game_state, clean_fan_state):
    clean_game_state["down"] = 4
    clean_game_state["scoreDifferential"] = -7  # trailing by 7
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert "G5_CriticalPlay" in result.suppressed_offers[0]["guardrail_reason"]


def test_g5_passes_when_blowout(offer, clean_game_state, clean_fan_state):
    clean_game_state["down"] = 4
    clean_game_state["scoreDifferential"] = 21  # comfortable lead
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


def test_g5_passes_on_non_4th_down(offer, clean_game_state, clean_fan_state):
    clean_game_state["down"] = 3
    clean_game_state["scoreDifferential"] = 3
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


def test_g5_fail_open_when_keys_missing(offer, clean_fan_state):
    gs = {"gameExcitementIndex": 0.5, "isRedZone": False}
    result = validate_offers([offer], gs, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


# ── G6 — Budget Cap ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("tier,max_offers,max_value", [
    ("Bronze",   3,  25.0),
    ("Silver",   4,  40.0),
    ("Gold",     6,  75.0),
    ("Platinum", 8, 150.0),
])
def test_g6_suppresses_when_offer_count_exceeded(offer, clean_game_state, tier, max_offers, max_value):
    fan_state = {
        "loyaltyTier": tier,
        "minutesSinceLastOffer": 999,
        "totalOffersThisGame": max_offers,  # already at cap; adding 1 offer pushes over
        "totalOfferValueThisGame": 0.0,
    }
    result = validate_offers([offer], clean_game_state, fan_state, sport="football")
    assert "G6_BudgetCap" in result.suppressed_offers[0]["guardrail_reason"]


@pytest.mark.parametrize("tier,max_offers,max_value", [
    ("Bronze",   3,  25.0),
    ("Silver",   4,  40.0),
    ("Gold",     6,  75.0),
    ("Platinum", 8, 150.0),
])
def test_g6_suppresses_when_value_exceeded(offer, clean_game_state, tier, max_offers, max_value):
    fan_state = {
        "loyaltyTier": tier,
        "minutesSinceLastOffer": 999,
        "totalOffersThisGame": 0,
        "totalOfferValueThisGame": max_value + 0.01,
    }
    result = validate_offers([offer], clean_game_state, fan_state, sport="football")
    assert "G6_BudgetCap" in result.suppressed_offers[0]["guardrail_reason"]


def test_g6_passes_within_cap(offer, clean_game_state, clean_fan_state):
    clean_fan_state["totalOffersThisGame"] = 2   # Gold cap is 6
    clean_fan_state["totalOfferValueThisGame"] = 10.0  # Gold cap is $75
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


# ── G7 — Premium Window ───────────────────────────────────────────────────────

def test_g7_suppresses_non_platinum_in_2min_warning(offer, clean_game_state):
    clean_game_state["gameClockQ2LessThan2m30s"] = True
    for tier in ("Bronze", "Silver", "Gold"):
        fan_state = {"loyaltyTier": tier, "minutesSinceLastOffer": 999,
                     "totalOffersThisGame": 0, "totalOfferValueThisGame": 0.0}
        result = validate_offers([offer], clean_game_state, fan_state, sport="football")
        assert "G7_PremiumWindow" in result.suppressed_offers[0]["guardrail_reason"], \
            f"{tier} should be suppressed in 2-min warning"


def test_g7_platinum_passes_in_2min_warning(offer, clean_game_state):
    clean_game_state["gameClockQ2LessThan2m30s"] = True
    fan_state = {"loyaltyTier": "Platinum", "minutesSinceLastOffer": 999,
                 "totalOffersThisGame": 0, "totalOfferValueThisGame": 0.0}
    result = validate_offers([offer], clean_game_state, fan_state, sport="football")
    assert len(result.clean_offers) == 1


def test_g7_passes_outside_2min_warning(offer, clean_game_state, clean_fan_state):
    clean_game_state["gameClockQ2LessThan2m30s"] = False
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


# ── Alcohol Policy ────────────────────────────────────────────────────────────

def test_alcohol_blocked_in_q4(alcohol_offer, clean_game_state, clean_fan_state):
    clean_game_state["quarter"] = 4
    result = validate_offers([alcohol_offer], clean_game_state, clean_fan_state, sport="football")
    assert "AlcoholPolicy" in result.suppressed_offers[0]["guardrail_reason"]


def test_alcohol_blocked_in_overtime(alcohol_offer, clean_game_state, clean_fan_state):
    clean_game_state["quarter"] = 5  # overtime
    result = validate_offers([alcohol_offer], clean_game_state, clean_fan_state, sport="football")
    assert "AlcoholPolicy" in result.suppressed_offers[0]["guardrail_reason"]


def test_alcohol_allowed_in_q2(alcohol_offer, clean_game_state, clean_fan_state):
    clean_game_state["quarter"] = 2
    result = validate_offers([alcohol_offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


def test_alcohol_allowed_in_q3(alcohol_offer, clean_game_state, clean_fan_state):
    clean_game_state["quarter"] = 3
    result = validate_offers([alcohol_offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


def test_non_alcohol_food_offer_not_blocked_in_q4(food_offer, clean_game_state, clean_fan_state):
    clean_game_state["quarter"] = 4
    result = validate_offers([food_offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


def test_alcohol_fail_open_when_quarter_missing(alcohol_offer, clean_fan_state):
    gs = {"gameExcitementIndex": 0.5, "isRedZone": False}  # no quarter
    result = validate_offers([alcohol_offer], gs, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


# ── Stadium Incident Override ─────────────────────────────────────────────────

def test_incident_override_blocks_restricted_category(food_offer, clean_game_state, clean_fan_state):
    clean_game_state["activeIncident"] = {
        "incidentId": "INC-001",
        "status": "active",
        "affectedSections": ["S108", "S109", "S110"],
        "restrictedOfferCategories": ["food_beverage"],
    }
    result = validate_offers([food_offer], clean_game_state, clean_fan_state, sport="football")
    assert "IncidentOverride" in result.suppressed_offers[0]["guardrail_reason"]


def test_incident_override_allows_non_restricted_category(offer, clean_game_state, clean_fan_state):
    clean_game_state["activeIncident"] = {
        "restrictedOfferCategories": ["food_beverage"],  # merchandise is not restricted
    }
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


def test_no_incident_passes(offer, clean_game_state, clean_fan_state):
    clean_game_state["activeIncident"] = None
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1


# ── Evaluation order (first-firing-wins) ─────────────────────────────────────

def test_g1_fires_before_g3_when_both_active(offer, clean_game_state, clean_fan_state):
    """G1 (Scoring Zone) should fire before G3 (Excitement) per policy §3 order."""
    clean_game_state["isRedZone"] = True
    clean_game_state["gameExcitementIndex"] = 0.90  # G3 would also fire
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert "G1_ScoringZone" in result.suppressed_offers[0]["guardrail_reason"]


def test_g1_fires_before_g4_when_both_active(offer, clean_game_state):
    clean_game_state["isRedZone"] = True
    fan_state = {"loyaltyTier": "Gold", "minutesSinceLastOffer": 5}  # G4 would also fire
    result = validate_offers([offer], clean_game_state, fan_state, sport="football")
    assert "G1_ScoringZone" in result.suppressed_offers[0]["guardrail_reason"]


def test_g3_fires_before_g4_when_both_active(offer, clean_game_state):
    clean_game_state["gameExcitementIndex"] = 0.90  # G3 fires
    fan_state = {"loyaltyTier": "Gold", "minutesSinceLastOffer": 5}  # G4 would also fire
    result = validate_offers([offer], clean_game_state, fan_state, sport="football")
    assert "G3_ExcitementSpike" in result.suppressed_offers[0]["guardrail_reason"]


# ── Audit record contracts ────────────────────────────────────────────────────

def test_audit_record_written_on_pass(offer, clean_game_state, clean_fan_state):
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.audit_records) == 1
    rec = result.audit_records[0]
    assert isinstance(rec, GuardrailAuditRecord)
    assert rec.offer_id == "offer_001"
    assert rec.result == "pass"
    assert rec.evaluated_at  # non-empty ISO timestamp


def test_audit_record_written_on_suppression(offer, clean_game_state, clean_fan_state):
    clean_game_state["isRedZone"] = True
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.audit_records) == 1
    rec = result.audit_records[0]
    assert rec.result == "suppressed"
    assert rec.guardrail == "G1_ScoringZone"
    assert rec.policy_ref == "§3 Guardrail 1"
    assert "game_state" in rec.context_snapshot
    assert "fan_state" in rec.context_snapshot


def test_audit_record_has_iso_timestamp(offer, clean_game_state, clean_fan_state):
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    ts = result.audit_records[0].evaluated_at
    assert "T" in ts and ("Z" in ts or "+00:00" in ts)  # ISO-8601 UTC (Z or +00:00)


# ── Multiple independent offers ───────────────────────────────────────────────

def test_multiple_offers_evaluated_independently(offer, food_offer, clean_game_state, clean_fan_state):
    """One offer may pass while another is suppressed — they don't share state."""
    clean_game_state["activeIncident"] = {
        "restrictedOfferCategories": ["food_beverage"],
    }
    result = validate_offers([offer, food_offer], clean_game_state, clean_fan_state, sport="football")
    assert len(result.clean_offers) == 1
    assert result.clean_offers[0]["id"] == "offer_001"
    assert len(result.suppressed_offers) == 1
    assert result.suppressed_offers[0]["id"] == "offer_002"
    assert len(result.audit_records) == 2


def test_empty_offer_list_returns_empty_result(clean_game_state, clean_fan_state):
    result = validate_offers([], clean_game_state, clean_fan_state, sport="football")
    assert result.clean_offers == []
    assert result.suppressed_offers == []
    assert result.audit_records == []


def test_suppressed_offer_retains_original_fields(offer, clean_game_state, clean_fan_state):
    """Suppressed offers keep all original fields plus the guardrail annotations."""
    clean_game_state["isRedZone"] = True
    result = validate_offers([offer], clean_game_state, clean_fan_state, sport="football")
    s = result.suppressed_offers[0]
    assert s["id"] == offer["id"]
    assert s["title"] == offer["title"]
    assert s["category"] == offer["category"]
    assert s["guardrail_suppressed"] is True
    assert s["guardrail_reason"]
    assert s["policy_ref"]


# ── Basketball — sport-specific guardrail tests ───────────────────────────────

@pytest.fixture
def basketball_game_state():
    """All-pass game state for basketball basketball."""
    return {
        "gameExcitementIndex": 0.60,
        "isFastBreak": False,
        "lastPlayType": "field_goal",
        "timeSinceScore": 120,
        "shotClock": 20,
        "scoreDifferential": 12,
        "quarter": 2,
        "gameClockQ4LessThan2m00s": False,
        "isFreeThrow": False,
        "activeIncident": None,
    }


@pytest.fixture
def basketball_fan_state():
    return {
        "loyaltyTier": "Gold",
        "minutesSinceLastOffer": 30,  # Gold gap for basketball = 15 min
        "totalOffersThisGame": 0,
        "totalOfferValueThisGame": 0.0,
    }


def test_basketball_g1_fast_break_suppresses(offer, basketball_game_state, basketball_fan_state):
    basketball_game_state["isFastBreak"] = True
    result = validate_offers([offer], basketball_game_state, basketball_fan_state, sport="basketball")
    assert "G1_ScoringZone" in result.suppressed_offers[0]["guardrail_reason"]


def test_basketball_g1_no_fast_break_passes(offer, basketball_game_state, basketball_fan_state):
    basketball_game_state["isFastBreak"] = False
    result = validate_offers([offer], basketball_game_state, basketball_fan_state, sport="basketball")
    assert len(result.clean_offers) == 1


def test_basketball_g2_basket_celebration_suppresses(offer, basketball_game_state, basketball_fan_state):
    """Basketball celebration window is shorter than football's."""
    basketball_game_state["lastPlayType"] = "basket"
    basketball_game_state["timeSinceScore"] = 10
    result = validate_offers([offer], basketball_game_state, basketball_fan_state, sport="basketball")
    assert "G2_PostScore" in result.suppressed_offers[0]["guardrail_reason"]


def test_basketball_g2_passes_after_15s(offer, basketball_game_state, basketball_fan_state):
    basketball_game_state["lastPlayType"] = "basket"
    basketball_game_state["timeSinceScore"] = 16
    result = validate_offers([offer], basketball_game_state, basketball_fan_state, sport="basketball")
    assert len(result.clean_offers) == 1


def test_basketball_g3_threshold_is_082(offer, basketball_game_state, basketball_fan_state):
    """Basketball excitement threshold is higher than football's."""
    basketball_game_state["gameExcitementIndex"] = 0.79
    result = validate_offers([offer], basketball_game_state, basketball_fan_state, sport="basketball")
    assert len(result.clean_offers) == 1  # should NOT suppress for basketball

    basketball_game_state["gameExcitementIndex"] = 0.83  # above basketball threshold
    result = validate_offers([offer], basketball_game_state, basketball_fan_state, sport="basketball")
    assert "G3_ExcitementSpike" in result.suppressed_offers[0]["guardrail_reason"]


def test_basketball_g4_gold_gap_is_15min(offer, basketball_game_state):
    """basketball Gold gap is 15 min (vs football's 30 min)."""
    fan_state = {"loyaltyTier": "Gold", "minutesSinceLastOffer": 14,
                 "totalOffersThisGame": 0, "totalOfferValueThisGame": 0.0}
    result = validate_offers([offer], basketball_game_state, fan_state, sport="basketball")
    assert "G4_OfferFatigue" in result.suppressed_offers[0]["guardrail_reason"]

    fan_state["minutesSinceLastOffer"] = 15
    result = validate_offers([offer], basketball_game_state, fan_state, sport="basketball")
    assert len(result.clean_offers) == 1


def test_basketball_g5_shot_clock_suppresses(offer, basketball_game_state, basketball_fan_state):
    basketball_game_state["shotClock"] = 4  # <= 5 triggers G5
    basketball_game_state["scoreDifferential"] = 3  # within 5-point margin
    result = validate_offers([offer], basketball_game_state, basketball_fan_state, sport="basketball")
    assert "G5_CriticalPlay" in result.suppressed_offers[0]["guardrail_reason"]


def test_basketball_g5_blowout_passes(offer, basketball_game_state, basketball_fan_state):
    basketball_game_state["shotClock"] = 4
    basketball_game_state["scoreDifferential"] = 20  # not close
    result = validate_offers([offer], basketball_game_state, basketball_fan_state, sport="basketball")
    assert len(result.clean_offers) == 1


# ── Soccer — sport-specific guardrail tests ───────────────────────────────────

@pytest.fixture
def soccer_game_state():
    """All-pass game state for soccer soccer."""
    return {
        "gameExcitementIndex": 0.55,
        "isInPenaltyBox": False,
        "lastPlayType": "pass",
        "timeSinceScore": 300,
        "isPenaltyKick": False,
        "scoreDifferential": 2,
        "quarter": 1,           # soccer uses 'half' field via alcohol cutoff
        "isStoppageTime": False,
        "isVARReview": False,
        "isInjuryStoppage": False,
        "activeIncident": None,
    }


@pytest.fixture
def soccer_fan_state():
    return {
        "loyaltyTier": "Gold",
        "minutesSinceLastOffer": 25,  # Gold gap for soccer = 20 min
        "totalOffersThisGame": 0,
        "totalOfferValueThisGame": 0.0,
    }


def test_soccer_g1_penalty_box_suppresses(offer, soccer_game_state, soccer_fan_state):
    soccer_game_state["isInPenaltyBox"] = True
    result = validate_offers([offer], soccer_game_state, soccer_fan_state, sport="soccer")
    assert "G1_ScoringZone" in result.suppressed_offers[0]["guardrail_reason"]


def test_soccer_g2_goal_90s_window(offer, soccer_game_state, soccer_fan_state):
    """Soccer goal celebration is 90 seconds (longest of all sports)."""
    soccer_game_state["lastPlayType"] = "goal"
    soccer_game_state["timeSinceScore"] = 60
    result = validate_offers([offer], soccer_game_state, soccer_fan_state, sport="soccer")
    assert "G2_PostScore" in result.suppressed_offers[0]["guardrail_reason"]

    soccer_game_state["timeSinceScore"] = 91  # after window
    result = validate_offers([offer], soccer_game_state, soccer_fan_state, sport="soccer")
    assert len(result.clean_offers) == 1


def test_soccer_alcohol_blocked_in_2nd_half(alcohol_offer, soccer_game_state, soccer_fan_state):
    """Soccer alcohol cutoff is half >= 2 (not quarter >= 4)."""
    soccer_game_state["quarter"] = 2  # alcohol_cutoff_quarter=2 for soccer
    result = validate_offers([alcohol_offer], soccer_game_state, soccer_fan_state, sport="soccer")
    assert "AlcoholPolicy" in result.suppressed_offers[0]["guardrail_reason"]


def test_soccer_alcohol_allowed_in_1st_half(alcohol_offer, soccer_game_state, soccer_fan_state):
    soccer_game_state["quarter"] = 1
    result = validate_offers([alcohol_offer], soccer_game_state, soccer_fan_state, sport="soccer")
    assert len(result.clean_offers) == 1


def test_soccer_var_review_extra_suppression(offer, soccer_game_state, soccer_fan_state):
    soccer_game_state["isVARReview"] = True
    result = validate_offers([offer], soccer_game_state, soccer_fan_state, sport="soccer")
    assert "VARReviewSuppression" in result.suppressed_offers[0]["guardrail_reason"]


# ── Hockey — sport-specific guardrail tests ───────────────────────────────────

@pytest.fixture
def hockey_game_state():
    """All-pass game state for hockey hockey."""
    return {
        "gameExcitementIndex": 0.55,
        "isPowerPlay": False,
        "lastPlayType": "shot_blocked",
        "timeSinceScore": 200,
        "isEmptyNet": False,
        "scoreDifferential": 3,
        "quarter": 2,           # hockey uses 'period' via alcohol cutoff
        "gameClockP3LessThan2m00s": False,
        "isPenaltyShot": False,
        "activeIncident": None,
    }


@pytest.fixture
def hockey_fan_state():
    return {
        "loyaltyTier": "Gold",
        "minutesSinceLastOffer": 20,  # Gold gap for hockey = 18 min
        "totalOffersThisGame": 0,
        "totalOfferValueThisGame": 0.0,
    }


def test_hockey_g1_power_play_suppresses(offer, hockey_game_state, hockey_fan_state):
    hockey_game_state["isPowerPlay"] = True
    result = validate_offers([offer], hockey_game_state, hockey_fan_state, sport="hockey")
    assert "G1_ScoringZone" in result.suppressed_offers[0]["guardrail_reason"]


def test_hockey_g2_goal_45s_window(offer, hockey_game_state, hockey_fan_state):
    """Hockey goal window is 45 seconds."""
    hockey_game_state["lastPlayType"] = "goal"
    hockey_game_state["timeSinceScore"] = 30
    result = validate_offers([offer], hockey_game_state, hockey_fan_state, sport="hockey")
    assert "G2_PostScore" in result.suppressed_offers[0]["guardrail_reason"]

    hockey_game_state["timeSinceScore"] = 46  # after window
    result = validate_offers([offer], hockey_game_state, hockey_fan_state, sport="hockey")
    assert len(result.clean_offers) == 1


def test_hockey_alcohol_blocked_in_period_3(alcohol_offer, hockey_game_state, hockey_fan_state):
    """Hockey alcohol cutoff is period >= 3 (alcohol_cutoff_quarter=3)."""
    hockey_game_state["quarter"] = 3
    result = validate_offers([alcohol_offer], hockey_game_state, hockey_fan_state, sport="hockey")
    assert "AlcoholPolicy" in result.suppressed_offers[0]["guardrail_reason"]


def test_hockey_alcohol_allowed_in_period_2(alcohol_offer, hockey_game_state, hockey_fan_state):
    hockey_game_state["quarter"] = 2
    result = validate_offers([alcohol_offer], hockey_game_state, hockey_fan_state, sport="hockey")
    assert len(result.clean_offers) == 1


def test_hockey_penalty_shot_extra_suppression(offer, hockey_game_state, hockey_fan_state):
    hockey_game_state["isPenaltyShot"] = True
    result = validate_offers([offer], hockey_game_state, hockey_fan_state, sport="hockey")
    assert "PenaltyShotSuppression" in result.suppressed_offers[0]["guardrail_reason"]
