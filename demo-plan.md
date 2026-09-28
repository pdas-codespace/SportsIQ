# Sports-IQ Clickthrough Plan

## Scenario

During a fictional multi-sport event break, Sports-IQ detects a drop in fan
engagement, enriches the signal with Fabric context, generates two personalized
offers, applies sport-aware guardrails, requests human approval, and records the
outcome.

## Demo data

- Fan: `bas_fan_0001`, `Fictional Fan 01-0001`, Gold tier
- Game: `basketball_game_0001`
- Teams: Harbor City Comets vs Metro Stars
- Venue: `VENUE_001`
- Data source: deterministic output from `data_generators/generate_all.py`

## Sequence

1. Sign in to the operator dashboard.
2. Select a fictional fan and simulate a break.
3. Show the ranked engagement trigger.
4. Start the workflow and narrate Fabric enrichment.
5. Review policy audit details on each offer.
6. Approve one offer and reject the other.
7. Redeem the approved offer and show the feedback event.

See `docs/Clickthrough-Demo-Guide.md` for the detailed script and
`demo/SportsIQ-AI-Voiceover-Demo-Sequence.md` for narration.
