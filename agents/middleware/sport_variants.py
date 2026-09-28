"""Sport-variant guardrail configurations.

Each sport defines its own set of guardrail thresholds and rules that reflect
the unique game rhythm, pause patterns, and fan behavior of that sport.

Active sport is selected via the SPORTS_IQ_SPORT environment variable
(default: "football"). See agents/.env.example.

Supported sports: football, basketball, soccer, hockey
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SportGuardrailConfig:
    """Guardrail thresholds and rules for a specific sport."""

    sport: str
    display_name: str

    # G1 — Scoring zone suppression
    scoring_zone_field: str        # game_state key name (e.g. "isRedZone")
    scoring_zone_label: str        # human-readable label for audit trail

    # G2 — Post-score celebration window
    score_play_type: str           # value of lastPlayType that triggers (e.g. "touchdown")
    celebration_window_seconds: int

    # G3 — Excitement index threshold
    excitement_threshold: float

    # G4 — Offer fatigue gaps (minutes) by loyalty tier
    fatigue_gap: dict[str, int]

    # G5 — Critical play suppression
    critical_play_field: str       # game_state key (e.g. "down" for football)
    critical_play_value: Any       # value that matches (e.g. 4 for 4th down)
    critical_play_comparison: str  # "==" for exact match, "<=" for threshold (e.g. shot clock)
    critical_play_score_margin: int  # |scoreDifferential| threshold
    critical_play_label: str       # human-readable label

    # G6 — Budget caps by loyalty tier
    budget_cap: dict[str, dict[str, Any]]

    # G7 — Premium window suppression
    premium_window_field: str      # game_state key (e.g. "gameClockQ2LessThan2m30s")
    premium_window_label: str

    # Alcohol policy — quarter cutoff (offers blocked at >= this quarter)
    alcohol_cutoff_quarter: int

    # Game structure
    periods_name: str              # "quarter", "period", "half"
    total_periods: int
    halftime_duration_minutes: int

    # Additional sport-specific suppression rules (optional)
    extra_suppressions: list[dict[str, Any]] = field(default_factory=list)


# ── Football ─────────────────────────────────────────────────────────────────

FOOTBALL = SportGuardrailConfig(
    sport="football",
    display_name="Football",
    scoring_zone_field="isRedZone",
    scoring_zone_label="Red Zone (inside opponent 20-yard line)",
    score_play_type="touchdown",
    celebration_window_seconds=60,
    excitement_threshold=0.78,
    fatigue_gap={"Bronze": 60, "Silver": 45, "Gold": 30, "Platinum": 20},
    critical_play_field="down",
    critical_play_value=4,
    critical_play_comparison="==",
    critical_play_score_margin=7,
    critical_play_label="4th-down critical play",
    budget_cap={
        "Bronze":   {"max_value": 25.0,  "max_offers": 3},
        "Silver":   {"max_value": 40.0,  "max_offers": 4},
        "Gold":     {"max_value": 75.0,  "max_offers": 6},
        "Platinum": {"max_value": 150.0, "max_offers": 8},
    },
    premium_window_field="gameClockQ2LessThan2m30s",
    premium_window_label="Pre-halftime 2-minute warning (Q2 < 2:30)",
    alcohol_cutoff_quarter=4,
    periods_name="quarter",
    total_periods=4,
    halftime_duration_minutes=30,
)

# ── Basketball (basketball) ─────────────────────────────────────────────────────────

BASKETBALL = SportGuardrailConfig(
    sport="basketball",
    display_name="basketball Basketball",
    scoring_zone_field="isFastBreak",
    scoring_zone_label="Fast break in progress",
    score_play_type="basket",
    celebration_window_seconds=15,
    excitement_threshold=0.82,
    fatigue_gap={"Bronze": 30, "Silver": 20, "Gold": 15, "Platinum": 10},
    critical_play_field="shotClock",
    critical_play_value=5,             # shot clock <= 5 seconds
    critical_play_comparison="<=",
    critical_play_score_margin=5,
    critical_play_label="Shot clock < 5s in close game",
    budget_cap={
        "Bronze":   {"max_value": 20.0,  "max_offers": 5},
        "Silver":   {"max_value": 35.0,  "max_offers": 7},
        "Gold":     {"max_value": 60.0,  "max_offers": 10},
        "Platinum": {"max_value": 120.0, "max_offers": 14},
    },
    premium_window_field="gameClockQ4LessThan2m00s",
    premium_window_label="Final 2 minutes of Q4 — crunch time",
    alcohol_cutoff_quarter=4,
    periods_name="quarter",
    total_periods=4,
    halftime_duration_minutes=20,
    extra_suppressions=[
        {
            "id": "FreeThrowSuppression",
            "field": "isFreeThrow",
            "condition": "isFreeThrow == true",
            "label": "Free throw in progress — brief attention lock",
            "policy_ref": "§3 Basketball-specific",
        },
    ],
)

# ── Soccer (soccer / Premier League) ────────────────────────────────────────────

SOCCER = SportGuardrailConfig(
    sport="soccer",
    display_name="Soccer / Football (soccer)",
    scoring_zone_field="isInPenaltyBox",
    scoring_zone_label="Ball in penalty box (scoring threat)",
    score_play_type="goal",
    celebration_window_seconds=90,
    excitement_threshold=0.80,
    fatigue_gap={"Bronze": 45, "Silver": 30, "Gold": 20, "Platinum": 12},
    critical_play_field="isPenaltyKick",
    critical_play_value=True,
    critical_play_comparison="==",
    critical_play_score_margin=2,
    critical_play_label="Penalty kick or free kick in close game",
    budget_cap={
        "Bronze":   {"max_value": 15.0,  "max_offers": 3},
        "Silver":   {"max_value": 30.0,  "max_offers": 5},
        "Gold":     {"max_value": 50.0,  "max_offers": 7},
        "Platinum": {"max_value": 100.0, "max_offers": 10},
    },
    premium_window_field="isStoppageTime",
    premium_window_label="Stoppage time — no non-premium offers",
    alcohol_cutoff_quarter=2,          # halves: block after H2 starts (no Q3/Q4)
    periods_name="half",
    total_periods=2,
    halftime_duration_minutes=15,
    extra_suppressions=[
        {
            "id": "VARReviewSuppression",
            "field": "isVARReview",
            "condition": "isVARReview == true",
            "label": "VAR review in progress — fan attention on screen",
            "policy_ref": "§3 Soccer-specific",
        },
        {
            "id": "InjuryTimeSuppression",
            "field": "isInjuryStoppage",
            "condition": "isInjuryStoppage == true AND scoreDifferential <= 1",
            "label": "Injury stoppage in close game — respectful suppression",
            "policy_ref": "§3 Soccer-specific",
        },
    ],
)

# ── Hockey (hockey) ─────────────────────────────────────────────────────────────

HOCKEY = SportGuardrailConfig(
    sport="hockey",
    display_name="hockey Hockey",
    scoring_zone_field="isPowerPlay",
    scoring_zone_label="Power play in progress (man advantage)",
    score_play_type="goal",
    celebration_window_seconds=45,
    excitement_threshold=0.80,
    fatigue_gap={"Bronze": 40, "Silver": 25, "Gold": 18, "Platinum": 12},
    critical_play_field="isEmptyNet",
    critical_play_value=True,
    critical_play_comparison="==",
    critical_play_score_margin=2,
    critical_play_label="Empty net situation in close game",
    budget_cap={
        "Bronze":   {"max_value": 20.0,  "max_offers": 4},
        "Silver":   {"max_value": 35.0,  "max_offers": 6},
        "Gold":     {"max_value": 60.0,  "max_offers": 9},
        "Platinum": {"max_value": 120.0, "max_offers": 12},
    },
    premium_window_field="gameClockP3LessThan2m00s",
    premium_window_label="Final 2 minutes of P3 — crunch time",
    alcohol_cutoff_quarter=3,          # 3 periods: block after P3 start
    periods_name="period",
    total_periods=3,
    halftime_duration_minutes=18,      # intermission between periods
    extra_suppressions=[
        {
            "id": "PenaltyShotSuppression",
            "field": "isPenaltyShot",
            "condition": "isPenaltyShot == true",
            "label": "Penalty shot in progress — peak attention",
            "policy_ref": "§3 Hockey-specific",
        },
    ],
)


# ── Registry ─────────────────────────────────────────────────────────────────

SPORT_CONFIGS: dict[str, SportGuardrailConfig] = {
    "football": FOOTBALL,
    "basketball": BASKETBALL,
    "soccer": SOCCER,
    "hockey": HOCKEY,
}


def get_sport_config(sport: str | None = None) -> SportGuardrailConfig:
    """Return the guardrail config for the given sport.

    Falls back to the SPORTS_IQ_SPORT env var, then to "football".
    Raises ValueError if the sport is not recognized.
    """
    import os

    sport = (sport or os.getenv("SPORTS_IQ_SPORT", "football")).lower().strip()
    if sport not in SPORT_CONFIGS:
        raise ValueError(
            f"Unknown sport '{sport}'. "
            f"Valid options: {', '.join(sorted(SPORT_CONFIGS))}"
        )
    return SPORT_CONFIGS[sport]
