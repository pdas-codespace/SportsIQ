#!/usr/bin/env python3
"""Generate deterministic, fictional, multi-sport Sports-IQ seed data."""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

SEED = 20260927
SPORTS = ("basketball", "football", "soccer", "hockey")
TIERS = ("Bronze", "Silver", "Gold", "Platinum")
TEAM_NAMES = ("Harbor City Comets", "Metro Stars")
VENUE_ID = "VENUE_001"


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def generate(output: Path, fans_per_sport: int) -> dict[str, int]:
    rng = random.Random(SEED)
    start = datetime(2026, 9, 1, 18, 0, tzinfo=timezone.utc)
    fan_rows: list[dict] = []
    game_rows: list[dict] = []
    promotion_rows: list[dict] = []
    engagement_rows: list[dict] = []
    pos_rows: list[dict] = []
    excitement_rows: list[dict] = []

    for sport_index, sport in enumerate(SPORTS, start=1):
        game_id = f"{sport}_game_{sport_index:04d}"
        game_start = start + timedelta(days=sport_index)
        game_rows.append(
            {
                "gameId": game_id,
                "sport": sport,
                "homeTeam": TEAM_NAMES[0],
                "awayTeam": TEAM_NAMES[1],
                "venueId": VENUE_ID,
                "gameDateUtc": game_start.isoformat(),
                "gameStatus": "scheduled",
            }
        )

        for minute in (5, 20, 35, 50):
            excitement_rows.append(
                {
                    "readingId": f"exc_{sport_index}_{minute}",
                    "gameId": game_id,
                    "sport": sport,
                    "timestamp": (game_start + timedelta(minutes=minute)).isoformat(),
                    "gameMinute": minute,
                    "period": 1 + minute // 20,
                    "isBreak": minute in (20, 50),
                    "scoreDifferential": rng.randint(-8, 8),
                    "excitementIndex": round(rng.uniform(0.25, 0.9), 3),
                }
            )

        for fan_index in range(1, fans_per_sport + 1):
            fan_id = f"{sport[:3]}_fan_{fan_index:04d}"
            tier = TIERS[(fan_index - 1) % len(TIERS)]
            section = f"SEC_{chr(65 + ((fan_index - 1) % 4))}{1 + fan_index % 5}"
            fan_rows.append(
                {
                    "fanId": fan_id,
                    "fanName": f"Fictional Fan {sport_index:02d}-{fan_index:04d}",
                    "sport": sport,
                    "loyaltyTier": tier,
                    "preferredSectionId": section,
                    "avgSpendPerGame": round(rng.uniform(18, 145), 2),
                    "avgConcessionSpend": round(rng.uniform(8, 55), 2),
                    "avgMerchandiseSpend": round(rng.uniform(0, 95), 2),
                    "offerFatigueGapMinutes": {"Bronze": 60, "Silver": 45, "Gold": 30, "Platinum": 20}[tier],
                    "baseEngagementScore": round(rng.uniform(0.5, 0.92), 3),
                    "churnRiskScore": round(rng.uniform(0.05, 0.8), 3),
                }
            )
            event_time = game_start + timedelta(minutes=10 + fan_index)
            engagement_rows.append(
                {
                    "eventId": f"eng_{sport_index}_{fan_index:04d}",
                    "fanId": fan_id,
                    "gameId": game_id,
                    "sport": sport,
                    "eventTimestamp": event_time.isoformat(),
                    "sourceSystem": "fictional_team_app",
                    "sectionId": section,
                    "eventType": "app_interaction",
                    "engagementScore": round(rng.uniform(0.25, 0.9), 3),
                    "gameMinute": 10 + fan_index,
                    "period": 1,
                }
            )
            if fan_index % 3 == 0:
                tx_id = f"tx_{sport_index}_{fan_index:04d}"
                pos_rows.append(
                    {
                        "transactionId": tx_id,
                        "fanId": fan_id,
                        "gameId": game_id,
                        "transactionTimestamp": (event_time + timedelta(minutes=3)).isoformat(),
                        "sourceSystem": "fictional_pos",
                        "sectionId": section,
                        "category": "food_beverage",
                        "itemName": "Venue Combo",
                        "quantity": 1,
                        "unitPrice": 14.0,
                        "totalAmount": 14.0,
                        "offerRedeemed": False,
                        "promoId": "",
                        "gameMinute": 13 + fan_index,
                        "period": 1,
                    }
                )
            promotion_rows.append(
                {
                    "promoId": f"promo_{sport_index}_{fan_index:04d}",
                    "fanId": fan_id,
                    "gameId": game_id,
                    "offerCategory": "food_beverage",
                    "offerValue": 5.0,
                    "outcome": "redeemed" if fan_index % 4 == 0 else "ignored",
                    "lastOfferTimestamp": (game_start - timedelta(days=7)).isoformat(),
                    "triggerContext": "synthetic_baseline",
                }
            )

    static_dir = output / "static"
    streaming_dir = output / "streaming"
    write_csv(static_dir / "fan_profile.csv", fan_rows)
    write_csv(static_dir / "game_context.csv", game_rows)
    write_csv(static_dir / "promotion_history.csv", promotion_rows)
    write_jsonl(streaming_dir / "fan_engagement_events.jsonl", engagement_rows)
    write_jsonl(streaming_dir / "pos_transactions.jsonl", pos_rows)
    write_jsonl(streaming_dir / "game_excitement_index.jsonl", excitement_rows)

    manifest = {
        "seed": SEED,
        "fictional": True,
        "sports": list(SPORTS),
        "counts": {
            "fan_profile": len(fan_rows),
            "game_context": len(game_rows),
            "promotion_history": len(promotion_rows),
            "fan_engagement_events": len(engagement_rows),
            "pos_transactions": len(pos_rows),
            "game_excitement_index": len(excitement_rows),
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest["counts"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/generated"))
    parser.add_argument("--fans-per-sport", type=int, default=12)
    args = parser.parse_args()
    if args.fans_per_sport < 1:
        parser.error("--fans-per-sport must be positive")
    counts = generate(args.output, args.fans_per_sport)
    print(f"Generated deterministic fictional data in {args.output}")
    for name, count in counts.items():
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
