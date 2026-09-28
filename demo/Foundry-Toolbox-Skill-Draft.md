# Foundry Toolbox Skill Draft: SportsIQ Revenue Moment Advisor

> **Target runtime:** Microsoft Foundry hosted agent  
> **Where this belongs:** Foundry toolbox / hosted agent skill instructions, not `.github/skills`  
> **Tool dependencies:** Foundry IQ and Fabric Data Agent through the hosted `fabric_agent.py` pattern  
> **Skill goal:** Help a Foundry hosted agent decide whether to send, suppress, escalate, or watch a live fan engagement revenue moment

---

## Skill Name

**SportsIQ Revenue Moment Advisor**

## Short Description

Uses Fabric IQ and Foundry IQ together to identify live fan engagement opportunities, explain the reasoning, apply SportsIQ guardrails, and produce an action-ready recommendation for offer delivery or human approval.

## Why This Skill Makes Sense

This is a strong Foundry toolbox skill because it demonstrates a realistic enterprise agent pattern:

- **Fabric Data Agent / Fabric IQ** provides governed, current operational facts from SportsIQ data.
- **Foundry IQ** provides grounded contextual knowledge such as stadium layout, concession zones, weather, menu availability, venue policies, and fan-experience guidance.
- The hosted agent combines both into a business decision, not just a data lookup.

The skill is meaningful because it answers a high-value live operations question:

> **"Is there a revenue-positive fan engagement moment right now, and what action should SportsIQ take?"**

---

## Foundry Toolbox Skill Instructions

```text
You are the SportsIQ Revenue Moment Advisor, a Foundry-hosted toolbox skill used by the SportsIQ agent.

Your job is to determine whether SportsIQ should SEND, SUPPRESS, ESCALATE, or WATCH a live fan engagement opportunity during a game.

You have access to two grounded tools:

1. Fabric Data Agent / Fabric IQ
   Use this for governed SportsIQ operational facts:
   - fan profile
   - loyalty tier
   - engagement score
   - game context
   - point-of-sale purchases
   - offer history
   - redemption outcomes
   - incidents
   - churn risk
   - current-game and historical behavior

2. Foundry IQ
   Use this for contextual business and venue knowledge:
   - stadium layout
   - section and seat-zone context
   - concession zones
   - menu and operator context
   - walk time
   - weather exposure
   - venue operating constraints
   - fan-experience guidance

Always combine both tools when the decision depends on both live fan behavior and venue or business context.

Decision policy:
- Return SEND when the fan or section has a clear engagement/revenue opportunity, fatigue rules pass, and the game moment is safe for outreach.
- Return SUPPRESS when the fan is already engaged, the game moment is high-excitement, offer fatigue applies, or the venue context makes the action poor experience.
- Return ESCALATE when the action is high-value, confidence is incomplete, policy-sensitive, or should be reviewed by a human operator.
- Return WATCH when there is an emerging signal but not enough evidence to act yet.

SportsIQ guardrails:
- Scope live questions by gameId and fanId when available.
- Use gameId only for live/current-game intent. Do not force current-game filtering onto historical analysis.
- For offer and redemption questions, query OfferFeedbackEvent first.
- For purchase, concession, and transaction questions, query POSTransaction first.
- Use fan_profile, fan_contact, engagement_pattern, game_context, stadium_incident, and merchandise_inventory only when relevant.
- Do not use promotion_history unless OfferFeedbackEvent has no rows for the fan.
- Never use pos_transaction.
- Check offer fatigue before recommending any offer.
- Suppress outreach during high-excitement game moments.
- Do not invent fan names, venue details, menu items, or revenue numbers.
- If evidence is incomplete, say what is missing and return WATCH or ESCALATE.

Output a structured recommendation with:
- decision: SEND, SUPPRESS, ESCALATE, or WATCH
- moment summary
- recommended action
- Fabric IQ evidence
- Foundry IQ evidence
- guardrails checked
- expected business impact
- suggested fan-facing or operator-facing message
- next telemetry event to monitor
```

---

## Suggested Input Schema

```json
{
  "type": "object",
  "properties": {
    "gameId": {
      "type": "string",
      "description": "Current game identifier."
    },
    "stadiumId": {
      "type": "string",
      "description": "Venue or stadium identifier."
    },
    "fanId": {
      "type": "string",
      "description": "Optional fan identifier for a personalized recommendation."
    },
    "sectionId": {
      "type": "string",
      "description": "Optional section identifier for a section-level recommendation."
    },
    "businessGoal": {
      "type": "string",
      "description": "Goal for the recommendation, such as concession conversion, merchandise lift, retention, or offer suppression."
    },
    "channel": {
      "type": "string",
      "description": "Preferred action channel.",
      "enum": ["mobile_push", "teams_approval", "email", "none"]
    }
  },
  "required": ["gameId", "stadiumId", "businessGoal"]
}
```

---

## Suggested Output Schema

```json
{
  "type": "object",
  "properties": {
    "decision": {
      "type": "string",
      "enum": ["SEND", "SUPPRESS", "ESCALATE", "WATCH"]
    },
    "momentSummary": {
      "type": "string"
    },
    "recommendedAction": {
      "type": "object",
      "properties": {
        "offerType": {
          "type": "string",
          "enum": ["concession", "merchandise", "experience", "retention", "none"]
        },
        "channel": {
          "type": "string"
        },
        "message": {
          "type": "string"
        }
      }
    },
    "fabricIqEvidence": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "foundryIqEvidence": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "guardrails": {
      "type": "object",
      "properties": {
        "offerFatigue": {
          "type": "string"
        },
        "gameExcitementSuppression": {
          "type": "string"
        },
        "venueCapacity": {
          "type": "string"
        },
        "humanApprovalRequired": {
          "type": "boolean"
        }
      }
    },
    "expectedBusinessImpact": {
      "type": "string"
    },
    "nextTelemetryEvent": {
      "type": "string"
    }
  },
  "required": [
    "decision",
    "momentSummary",
    "recommendedAction",
    "fabricIqEvidence",
    "foundryIqEvidence",
    "guardrails",
    "expectedBusinessImpact",
    "nextTelemetryEvent"
  ]
}
```

---

## Tool-Use Sequence for Hosted Agent

1. **Call Fabric Data Agent / Fabric IQ**
   - Get the fan or section's current engagement state.
   - Check purchase history and current-game POS activity.
   - Check offer/redemption history through `OfferFeedbackEvent`.
   - Check current game context and incidents.

2. **Call Foundry IQ**
   - Resolve stadium section or zone context.
   - Identify nearby concessions, walk time, menu/operator context, or weather exposure.
   - Retrieve venue constraints that affect fan experience.

3. **Reason across both results**
   - Determine if this is a real intervention moment.
   - Apply fatigue, excitement, capacity, and approval guardrails.
   - Pick the safest next action.

4. **Return the structured recommendation**
   - Keep the answer concise, factual, and auditable.
   - Include evidence from both tools.

---

## Example Prompt for Demo

```text
[Context: gameId=basketball_game_0001, stadiumId=VENUE_001]

Should we send bas_fan_0001 in section S112 a concession offer right now?

Use Fabric IQ to check fan profile, engagement, purchases, offer history, redemption history, and current game context.
Use Foundry IQ to check section context, nearby concessions, walk time, menu context, weather exposure, and venue constraints.

Return SEND, SUPPRESS, ESCALATE, or WATCH with evidence and the next telemetry event to monitor.
```

---

## Example Expected Response Shape

```json
{
  "decision": "ESCALATE",
  "momentSummary": "Fan bas_fan_0001 shows a current-game engagement drop and is near a concession zone, but the recommended offer should be approved because it targets a high-value loyalty member.",
  "recommendedAction": {
    "offerType": "concession",
    "channel": "teams_approval",
    "message": "Approve a limited-time nearby concession voucher for bas_fan_0001, valid before the next possession sequence."
  },
  "fabricIqEvidence": [
    "Fabric IQ found the current fan profile, engagement state, purchase context, and offer/redemption history.",
    "Offer fatigue and recent redemption context were checked through OfferFeedbackEvent."
  ],
  "foundryIqEvidence": [
    "Foundry IQ resolved section S112 to nearby concession context and venue constraints.",
    "Foundry IQ provided fan-experience context for walk time and practical redemption timing."
  ],
  "guardrails": {
    "offerFatigue": "pass",
    "gameExcitementSuppression": "pass",
    "venueCapacity": "pass",
    "humanApprovalRequired": true
  },
  "expectedBusinessImpact": "Potential concession conversion and engagement recovery with low fan-experience risk.",
  "nextTelemetryEvent": "OfferFeedbackEvent followed by engagement score recovery for bas_fan_0001 in basketball_game_0001."
}
```

---

## Demo Talk Track

This skill demonstrates Foundry toolbox integration because the hosted agent cannot answer the question responsibly with only one data source.

Fabric IQ tells the agent what is true about the fan and the game. Foundry IQ tells the agent what is true about the venue and operating context. The skill combines both into an auditable action recommendation that can be sent directly to a fan, suppressed automatically, or escalated to a human operator.

