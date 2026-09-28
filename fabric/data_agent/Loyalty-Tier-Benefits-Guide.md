# Harbor City Comets — Loyalty Tier Benefits Guide

**Program Name:** Comets Rewards
**Venue:** Harbor Center
**Effective:** 2025 professional football Season
**Last Updated:** 2025-08-15

---

## Program Overview

Comets Rewards is the Harbor City Comets' four-tier fan loyalty program. Tier assignment is based on season ticket tenure, total spend history, and engagement score. The program governs how Sports-IQ personalizes the in-game experience — including offer frequency, discount depth, delivery channel, and access to premium experiences.

Every fan in the `fan_profile` table has a `loyaltyTier` value of Bronze, Silver, Gold, or Platinum. This tier drives all downstream offer decisions.

---

## Tier Summary

| Attribute | Bronze | Silver | Gold | Platinum |
|-----------|--------|--------|------|----------|
| **Fan count (approx.)** | 300 fans (50%) | 120 fans (20%) | 120 fans (20%) | 60 fans (10%) |
| **Typical season ticket years** | 0–8 | 0–15 | 1–13 | 2–20+ |
| **PSL holder** | Rarely | Sometimes | Always | Always |
| **Suite holder** | No | No | No | Sometimes |
| **Avg spend per game** | $35–$60 | $64–$100 | $100–$180 | $200–$450+ |
| **Avg concession spend** | $19–$42 | $38–$67 | $61–$130 | $129–$280+ |
| **Avg merchandise spend** | $8–$24 | $15–$39 | $30–$69 | $43–$120+ |
| **Base engagement score** | 0.30–0.58 | 0.49–0.72 | 0.60–0.85 | 0.72–0.93 |
| **Churn risk score** | 0.56–0.85 | 0.26–0.54 | 0.10–0.27 | 0.07–0.12 |
| **Offer fatigue gap** | 60 minutes | 45 minutes | 30 minutes | 20 minutes |
| **Preferred channel** | App | App | App | Teams |

---

## Bronze Tier

### Eligibility
- Default tier for all fans with an active Harbor City Comets account
- No minimum season ticket tenure or spend required

### In-Game Offer Benefits

| Benefit | Detail |
|---------|--------|
| **Offer frequency** | Maximum 3 offers per game, minimum 60 minutes between offers |
| **Discount depth** | 10–15% off menu/retail price |
| **Offer categories** | Food & Beverage, standard Merchandise |
| **Experience upgrades** | Not eligible |
| **Fantasy milestone offers** | Eligible (if `fantasyEngagementScore > 0.5`) |
| **Pre-game / tailgate offers** | Eligible |
| **Budget cap** | $25 total discount value per game |
| **Delivery channel** | professional football OnePass app push notification |

### Behavioral Notes
- Bronze fans have the highest churn risk (avg 0.72). Sports-IQ uses offers strategically to **re-engage** fans showing disengagement signals.
- Low offer frequency (60-min gap) means each offer must be high-relevance. The system should only trigger offers when the engagement score drops significantly below the fan's baseline.
- Bronze fans are **not** eligible for 2-minute warning offers (Q2/Q4 premium window is reserved for Platinum).

### Upgrade Path
- Attend 6+ games in a season → auto-review for Silver
- Purchase a season ticket package → immediate Silver upgrade
- Total season spend > $600 → end-of-season Silver review

---

## Silver Tier

### Eligibility
- Season ticket holder with 1+ years tenure, OR
- Cumulative spend exceeding $500/season, OR
- Upgraded from Bronze via engagement criteria

### In-Game Offer Benefits

| Benefit | Detail |
|---------|--------|
| **Offer frequency** | Maximum 4 offers per game, minimum 45 minutes between offers |
| **Discount depth** | 10–20% off menu/retail price |
| **Offer categories** | Food & Beverage, Merchandise, Fantasy Milestone |
| **Experience upgrades** | Not eligible (Gold+ only) |
| **Fantasy milestone offers** | Eligible |
| **Pre-game / tailgate offers** | Eligible with 15% discount ceiling |
| **Budget cap** | $40 total discount value per game |
| **Delivery channel** | professional football OnePass app push notification |

### Behavioral Notes
- Silver fans show moderate engagement (avg score 0.60) with a healthier churn profile (avg 0.39) than Bronze.
- Some Silver fans hold PSL seats — the system should recognize PSL status as a secondary signal even within Silver tier.
- Silver fans respond well to **merchandise offers tied to scoring plays** — their avg merchandise spend ($15–$39) leaves headroom for upsell.
- Offer timing should align with the fan's historical purchase pattern (`engagement_pattern.historicalPurchaseMinute`) when available.

### Upgrade Path
- Maintain season tickets for 3+ consecutive years → Gold review
- Total season spend > $1,000 → end-of-season Gold review
- Purchase a PSL → immediate Gold upgrade

---

## Gold Tier

### Eligibility
- PSL holder (all Gold fans hold PSLs: `isPSLHolder == true`)
- Season ticket holder with significant tenure (typically 1–13 years)
- Consistently high per-game spend ($100–$180 avg)

### In-Game Offer Benefits

| Benefit | Detail |
|---------|--------|
| **Offer frequency** | Maximum 6 offers per game, minimum 30 minutes between offers |
| **Discount depth** | 15–25% off menu/retail price |
| **Offer categories** | Food & Beverage, Merchandise, Experience Upgrades, Fantasy Milestone |
| **Experience upgrades** | **Eligible** — club seat day pass, sideline photo opportunity, halftime field access |
| **Fantasy milestone offers** | Eligible with enhanced discount (15% vs. standard 10%) |
| **Pre-game / tailgate offers** | Eligible with 20% discount ceiling |
| **Budget cap** | $75 total discount value per game |
| **Delivery channel** | professional football OnePass app push notification |
| **Exclusive:** | Post-win merchandise flash sale (20% off, 15-minute window after final whistle) |

### Behavioral Notes
- Gold fans are the **revenue engine** — high spend, high engagement (avg 0.73), low churn (avg 0.20).
- Experience upgrades are a powerful differentiator for Gold. A sideline photo pass during halftime converts at 12%+ for this tier.
- Gold fans respond strongly to **win-probability-triggered merchandise offers**. When the Comets' win probability exceeds 80%, Gold fans buy victory merchandise at 2x the baseline rate.
- The 30-minute offer gap allows up to 6 touches in a 3.5-hour game — enough for a multi-category sequence (F&B early → Merch mid-game → Experience at halftime → Fantasy if triggered → Post-win flash sale).

### Upgrade Path
- PSL holder with 10+ years tenure → Platinum review
- Season spend > $2,500 → end-of-season Platinum review
- Suite purchase → immediate Platinum upgrade

---

## Platinum Tier

### Eligibility
- Long-tenure PSL holder (typically 10+ years) and/or suite holder
- Consistently highest per-game spend ($200–$450+ avg)
- By invitation or automatic qualification

### In-Game Offer Benefits

| Benefit | Detail |
|---------|--------|
| **Offer frequency** | Maximum 8 offers per game, minimum 20 minutes between offers |
| **Discount depth** | 15–30% off menu/retail price |
| **Offer categories** | All categories including premium Experience Upgrades |
| **Experience upgrades** | **Premium access** — suite day pass, meet-and-greet, on-field pregame access, exclusive player signing events |
| **Fantasy milestone offers** | Eligible with premium discount (20%) |
| **Pre-game / tailgate offers** | Eligible with 25% discount ceiling + exclusive tailgate lounge access |
| **Budget cap** | $150 total discount value per game |
| **Delivery channel** | **Microsoft Teams** (preferred) or professional football OnePass app |
| **Exclusive:** | 2-minute warning premium offer window (Q2 and Q4) |
| **Exclusive:** | Post-game meet-and-greet lottery entry (1 per game) |
| **Exclusive:** | Season-end appreciation event invitation |
| **Exclusive:** | Early renewal offer with locked-in pricing for next season |

### Behavioral Notes
- Platinum fans are the highest-value segment with the lowest churn risk (avg 0.09). Retention is the primary objective — every interaction should reinforce their VIP status.
- Many Platinum fans prefer Microsoft Teams as their delivery channel (`preferredChannel == 'teams'`). The system must respect this preference — never downgrade a Teams-preference fan to app push.
- Suite holders (`isSuiteHolder == true`) within Platinum receive specialized offers: in-suite catering upgrades, corporate hospitality packages, and branded suite accessories.
- The 20-minute offer gap is the most aggressive cadence. Despite this, Platinum fans have the highest historical offer response rate and the lowest opt-out rate. They **expect** a premium, personalized experience.
- Platinum fans are the **only** tier eligible for offers during the Q2 and Q4 2-minute warning windows. This is their exclusive benefit — treat it as a competitive advantage for the tier.

### Retention Program
- Any Platinum fan with `gamesAttendedSeason < 4` by Week 12 triggers a proactive retention outreach
- Churn risk score > 0.10 for a Platinum fan generates a priority alert to the Fan Relations team
- Season-end renewal offers include a 5% early-bird discount exclusive to Platinum

---

## Tier Comparison — Offer Policy Quick Reference

| Policy Rule | Bronze | Silver | Gold | Platinum |
|-------------|--------|--------|------|----------|
| Min gap between offers | 60 min | 45 min | 30 min | 20 min |
| Max offers per game | 3 | 4 | 6 | 8 |
| Max discount value per game | $25 | $40 | $75 | $150 |
| Max discount % (F&B) | 15% | 20% | 25% | 30% |
| Max discount % (Merch) | 15% | 20% | 25% | 30% |
| Experience upgrades | No | No | Yes | Yes (Premium) |
| 2-min warning offers | No | No | No | Yes (Exclusive) |
| Post-win flash sale | No | No | Yes | Yes |
| Fantasy enhanced discount | No | No | 15% | 20% |
| Preferred delivery channel | App | App | App | Teams |
| Alcohol offers (Q1–Q3) | Yes | Yes | Yes | Yes |
| Pre-game tailgate offers | Yes | Yes (15% cap) | Yes (20% cap) | Yes (25% cap) |

---

## How Sports-IQ Uses This Guide

When the AI agent evaluates whether to send an offer to a specific fan:

1. **Look up `fan_profile.loyaltyTier`** to determine the fan's tier
2. **Check offer fatigue** against the tier's minimum gap (this guide's values match `fan_profile.offerFatigueGapMinutes`)
3. **Verify budget cap** — has the fan hit their per-game discount limit?
4. **Select eligible categories** — is this fan eligible for the offer type? (Experience upgrades require Gold+)
5. **Apply discount range** — never exceed the tier's maximum discount percentage
6. **Route to correct channel** — respect `preferredChannel`, default to the tier's standard channel
7. **Check exclusive windows** — 2-minute warning is Platinum-only

This ensures every offer respects the fan's loyalty status and the program's value hierarchy.
