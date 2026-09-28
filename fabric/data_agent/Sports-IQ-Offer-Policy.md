# Sports-IQ Offer Policy v2.3

**Effective:** 2025 professional football Season (September 2025 – January 2026)
**Venue:** Harbor Center — Home of the Harbor City Comets
**Owner:** Stadium Revenue Operations
**Last Updated:** 2025-08-15

---

## 1. Purpose

This policy governs how and when the Sports-IQ AI platform delivers personalized offers to fans during live professional football games at Harbor Center. The system must maximize per-fan revenue while protecting the fan experience. A badly timed offer is worse than no offer at all.

---

## 2. Offer Delivery Windows

The professional football game clock creates distinct windows where fan attention shifts. Sports-IQ classifies each window by intervention eligibility.

### 2.1 Primary Intervention Windows (OPEN)

| Window | Duration | Frequency per Game | Conversion Expectation |
|--------|----------|--------------------|----------------------|
| TV Timeout | ~90 seconds | 20–24 per game | 18%+ |
| 2-Minute Warning (Q2, Q4) | ~2 minutes | 2 per game | 22%+ (premium window) |
| Halftime | ~30 minutes | 1 per game | 28%+ (multi-offer sequence allowed) |
| End of Quarter (Q1, Q3) | ~5 minutes | 2 per game | 15%+ |
| Injury Timeout | Variable (60–180 sec) | 2–4 per game | 12%+ (opportunistic) |
| Booth Review / Challenge | 90–120 seconds | 1–3 per game | 10%+ (short-form offers only) |

### 2.2 Suppressed Windows (BLOCKED)

During these windows, **no offers may be sent** regardless of fan eligibility or offer value.

| Window | Condition | Rationale |
|--------|-----------|-----------|
| Active Play (snap to whistle) | Ball is live | Fan attention is on the field |
| Red Zone Drive | `isRedZone == true` | Peak attention moment — fan is engaged |
| Post-Touchdown Celebration | `lastPlayType == 'touchdown' AND timeSinceTD < 60s` | Fan is celebrating; offer will be ignored |
| 4th-Down Critical Play | `down == 4 AND scoreDifferential <= 7` | High-stakes moment — suppression protects experience |
| Game Excitement Spike | `gameExcitementIndex > 0.78` | Close, dramatic game — fans are riveted |
| Pre-Halftime Crunch | `gameClockQ2 < 2:30 AND loyaltyTier != 'Platinum'` | 2-minute warning active — Platinum-only window |
| Post-Game Final Whistle | First 120 seconds after game end | Emotional processing — win or loss |

---

## 3. Guardrail Rules

Seven guardrails protect the fan experience. Each guardrail is evaluated in order before any offer is delivered. If any guardrail triggers, the offer is **suppressed**.

### Guardrail 1 — Red Zone Suppression

- **Condition:** `isRedZone == true`
- **Effect:** All offers blocked for all fans
- **Override:** None — this guardrail is absolute

### Guardrail 2 — Post-Touchdown Celebration Window

- **Condition:** `lastPlayType == 'touchdown' AND timeSinceTD < 60 seconds`
- **Effect:** All offers blocked for 60 seconds after any touchdown (either team)
- **Rationale:** Fans celebrate touchdowns for the home team and process opponent scores. Neither state is receptive to commercial offers.

### Guardrail 3 — Game Excitement Suppression

- **Condition:** `gameExcitementIndex > 0.78`
- **Effect:** All non-emergency offers suppressed
- **Rationale:** Close games with high drama keep fans locked in. Interrupting this state damages brand perception.

### Guardrail 4 — Offer Fatigue

- **Condition:** `minutesSinceLastOffer < tierMinimumGap`
- **Tier-specific gaps:**

| Loyalty Tier | Minimum Gap Between Offers | Rationale |
|-------------|---------------------------|-----------|
| Bronze | 60 minutes | Low engagement fans — infrequent, high-relevance only |
| Silver | 45 minutes | Moderate engagement — balanced cadence |
| Gold | 30 minutes | High-value fans — more frequent, personalized offers |
| Platinum | 20 minutes | Highest-value fans — responsive to frequent, premium offers |

- **Override:** None. The gap is measured from `OfferFeedbackEvent.offerTimestamp` (current game) or `promotion_history.lastOfferTimestamp` (cross-game fallback).

### Guardrail 5 — 4th-Down Critical Play

- **Condition:** `down == 4 AND scoreDifferential <= 7`
- **Effect:** All offers suppressed during the play sequence
- **Rationale:** 4th-down decisions in close games are the most dramatic moments in football. Fans must not be distracted.

### Guardrail 6 — Per-Fan Budget Cap

- **Condition:** `totalOffersThisGame * avgOfferValue > tierBudgetCap`
- **Budget caps per tier:**

| Loyalty Tier | Max Offer Value per Game | Max Offers per Game |
|-------------|-------------------------|---------------------|
| Bronze | $25 total discount value | 3 offers |
| Silver | $40 total discount value | 4 offers |
| Gold | $75 total discount value | 6 offers |
| Platinum | $150 total discount value | 8 offers |

- **Effect:** Once a fan hits their budget cap, no further offers are sent for the remainder of the game.

### Guardrail 7 — Pre-Halftime Premium Window

- **Condition:** `gameClockQ2 < 2:30`
- **Effect:** Only Platinum-tier fans receive offers during the Q2 2-minute warning. All other tiers are suppressed.
- **Rationale:** The 2-minute warning is a high-conversion window but also a high-attention moment. Reserve it for the fans most likely to convert.

---

## 4. Offer Categories

Sports-IQ delivers five categories of personalized offers. Each category has specific targeting rules.

### 4.1 Food & Beverage

- **Trigger:** Fan purchase pattern deviation (e.g., no purchase in > `avgPurchaseInterval` minutes)
- **Targeting:** Route fan to nearest concession zone with short wait time
- **Discount range:** 10–20% off menu price
- **Alcohol policy:** No alcoholic beverage offers after Q3 kickoff per professional football stadium policy. Alcohol sales cease at end of Q3.

### 4.2 Merchandise

- **Trigger:** Win probability > 80% (victory merchandise), scoring play by featured player, or halftime browse window
- **Targeting:** Items from nearest merchandise stand (`seat_section.nearestMerchStand`), filtered by `stockLevel > 0` and `discountEligible == true`
- **Discount range:** 10–25% off retail
- **Player relevance:** Prioritize items featuring players involved in the most recent scoring play

### 4.3 Experience Upgrade

- **Trigger:** Fan loyalty tier is Gold or Platinum, current section is Lower Bowl or above, and premium seating availability exists
- **Examples:** Club seat day pass, sideline photo opportunity, halftime field access
- **Discount range:** 15–30% off standard price
- **Limit:** One experience offer per fan per game

### 4.4 Fantasy Milestone

- **Trigger:** Fan's fantasy player (from `fantasyEngagementScore > 0.5`) scores a touchdown, exceeds 100 rushing/receiving yards, or hits a weekly high
- **Offer type:** Celebratory — branded merchandise or F&B combo tied to the milestone
- **Discount range:** 10–15%
- **Limit:** Two fantasy-triggered offers per fan per game

### 4.5 Pre-Game / Tailgate

- **Trigger:** `parkingArrivalEvent` detected AND `timeSinceArrival > 15 minutes` AND `timeToKickoff > 45 minutes`
- **Offer type:** Pre-game merchandise, early-entry concession deal, tailgate accessory
- **Discount range:** 10–20%
- **Special rule:** Tailgate offers cease 30 minutes before kickoff to avoid distracting fans heading to seats

---

## 5. Delivery Channel Rules

| Channel | Target Audience | Priority |
|---------|----------------|----------|
| professional football OnePass / Team App Push | All fans with `hasprofessional footballOnePass == true` | Primary |
| SMS (opt-in) | Fans without the app but with `phone` in `fan_contact` | Secondary |
| Microsoft Teams | Suite holders (`isSuiteHolder == true`) and corporate accounts | Premium channel |
| Concession Kiosk | Fan approaching self-service kiosk (proximity trigger) | Ambient |

- **Channel preference:** Always respect `fan_profile.preferredChannel`. If `preferredChannel == 'teams'`, use Teams even if the fan has the app installed.
- **Fallback:** If the primary channel fails delivery confirmation within 10 seconds, do not retry on a secondary channel for that offer cycle.

---

## 6. Stadium Incident Override

When a `stadium_incident` record has `status == 'active'`:

- All offers in `restrictedOfferCategories` are suppressed for fans in `affectedSections`
- The suppression is absolute — no tier override
- Example: A concession zone fire alarm suppresses all F&B offers for adjacent sections until incident is resolved

---

## 7. Feedback Loop Requirements

Every offer delivered by Sports-IQ must produce a feedback event:

1. **Offer sent** → `OfferFeedbackEvent` written with `outcome = 'pending'`
2. **Fan redeems** → POS scan updates `outcome = 'redeemed'`, `revenueImpact` calculated
3. **Fan ignores** → After 15 minutes with no redemption, `outcome = 'ignored'`
4. **Fan opts out** → `outcome = 'opted_out'` — triggers 2x fatigue gap multiplier for next offer

No offer may be fire-and-forget. The closed-loop design ensures the model improves with every game.

---

## 8. Compliance Notes

- **Data privacy:** Fan identity resolution uses `fanId` only. No PII is stored in real-time streaming tables. Contact information (`email`, `phone`) is accessed only at delivery time via `fan_contact` join.
- **Alcohol regulations:** Alcohol-related offers comply with venue and state regulations. No alcohol offers to fans flagged in the venue's responsible service system.
- **Opt-out:** Fans may opt out of AI-driven offers at any time via the professional football OnePass app settings. Opt-out is honored within 1 offer cycle (< 20 minutes for Platinum, < 60 minutes for Bronze).
- **Minors:** No offers are sent to fan accounts flagged as under-21 for alcohol categories or under-18 for all categories without parental consent on file.

---

## 9. Latency Target

The end-to-end latency from signal detection to offer delivery must be **under 10 seconds**:

| Stage | Budget |
|-------|--------|
| Signal ingestion (Eventstream) | < 2 seconds |
| Enrichment (Lakehouse join) | < 3 seconds |
| AI reasoning (Foundry agent) | < 3 seconds |
| Delivery (push notification) | < 2 seconds |
| **Total** | **< 10 seconds** |

If any stage exceeds its budget, the offer is still delivered but flagged for latency review in the telemetry pipeline.
