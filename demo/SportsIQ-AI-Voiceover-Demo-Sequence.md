# SportsIQ AI Voiceover Demo Sequence

> **Target runtime:** 4 min 45 sec, safely under 5 min  
> **Format:** Screen-recorded SportsIQ walkthrough with AI voiceover  
> **Voice style:** Confident, clear, executive-demo tone  
> **Recommended TTS output:** WAV/PCM for editing, then export final video as MP4  
> **Best use:** Record the screen first, generate the AI voiceover second, then edit the screen capture to the audio track

---

## Recommended Production Flow

1. **Prepare the app state**
   - Open SportsIQ to the live game operations dashboard.
   - Preload the screens for real-time events, fan profile enrichment, agent reasoning, offer approval, delivery status, and feedback analytics.
   - Keep demo data stable so the screen recording does not depend on a live refresh at the wrong moment.

2. **Record the screen without final narration**
   - Record at 16:9, ideally 1920 x 1080.
   - Use a scratch narration if it helps pacing, but do not rely on it for the final audio.
   - Capture each scene as a short clip so you can trim and reorder easily.

3. **Generate the AI voiceover**
   - Use Azure AI Speech / Foundry Speech text-to-speech.
   - Recommended voices: `en-US-JennyNeural`, `en-US-DavisNeural`, `en-US-GuyNeural`, or another polished en-US neural voice available in your Foundry speech resource.
   - Export as WAV where possible. Avoid MP3 until the final video export.
   - If using SSML, add short pauses between scenes and pronunciation hints for "SportsIQ", "KQL", "OneLake", "Eventhouse", and "Foundry".

4. **Edit audio-first**
   - Place the generated voiceover on the timeline first.
   - Trim or retime screen clips underneath the narration.
   - Use subtle zooms and callout boxes to focus attention on the active UI region.
   - Add captions after the voiceover is locked.

5. **Final polish**
   - Add light background music at 10-15% volume under the voiceover.
   - Normalize final voice loudness around -16 LUFS for web playback.
   - Keep transitions simple: quick dissolves, light zooms, and clean text overlays.

---

## Demo Scene Sequence

| Time | Scene | Screen Action | Key Message |
|---|---|---|---|
| 0:00-0:25 | Opening | Show SportsIQ title, architecture or landing dashboard | SportsIQ turns live game signals into personalized revenue actions. |
| 0:25-0:55 | Live operations | Show live game dashboard, engagement cards, event counters | The system monitors fan behavior at possession-level granularity. |
| 0:55-1:30 | Real-time signal detection | Show Eventstream/Eventhouse-style events, KQL result, engagement dip | Real-time signals identify a high-value intervention opportunity. |
| 1:30-2:05 | Context enrichment | Show fan profile, loyalty tier, seat zone, promotion history | Fabric enriches raw signals with fan, venue, and game context. |
| 2:05-2:45 | AI reasoning and decisioning | Show agent reasoning or workflow output | Fabric Data Agent and Foundry decide whether to act, suppress, or escalate. |
| 2:45-3:20 | Human approval | Show approval card with reason, guardrails, expected impact | Human-in-the-loop approval makes AI actions transparent and auditable. |
| 3:20-3:55 | Personalized delivery | Show mobile notification or offer payload | The fan receives the right offer at the right moment. |
| 3:55-4:25 | Closed-loop feedback | Show redemption or response event flowing back | Outcomes feed back into the real-time stream and improve future decisions. |
| 4:25-4:55 | Impact and close | Show metrics dashboard and Microsoft stack | SportsIQ connects Fabric, Foundry, approval, delivery, and analytics end to end. |

---

## Screen Recording Checklist

| # | Clip | Capture Notes |
|---|---|---|
| 1 | Title or landing view | Start clean with SportsIQ visible. Use a slow cursor movement or no cursor. |
| 2 | Live operations dashboard | Show engagement score, current quarter or possession, live events, and alert cards. |
| 3 | Real-time events | Show fan engagement events, POS transactions, crowd density, and game context flowing in. |
| 4 | KQL or query result | Highlight the disengaged fan scenario and the event that triggers analysis. |
| 5 | Fan context | Show FanProfile, loyalty tier, average spend, PromotionHistory, and SeatZone context. |
| 6 | Agent reasoning | Show the reasoning summary, confidence, guardrails, and recommendation. |
| 7 | Approval | Show approve, modify, or reject controls and the rationale for the offer. |
| 8 | Delivery | Show the offer payload or phone notification. |
| 9 | Feedback | Show redemption, ignored, returned-to-seat, or app-open event flowing back. |
| 10 | Impact dashboard | Show conversion, engagement recovery, incremental spend, latency, and telemetry. |

---

## Voiceover Script - Copy/Paste Block

Welcome to SportsIQ, an AI-powered fan engagement and revenue optimization platform for live sports venues.

In this demo, we will see how SportsIQ detects real-time fan behavior during an professional basketball game, enriches it with business context, reasons over engagement patterns, recommends the right intervention, and closes the loop with measurable feedback.

The goal is simple: turn live game signals into timely, personalized actions that improve fan experience and drive incremental revenue.

We start in the live game operations view.

SportsIQ monitors fan engagement at possession-level granularity, not just by quarter or timeout. The system watches signals such as app activity, seat dwell time, concession proximity, point-of-sale purchases, crowd density, and the game excitement index.

This matters because timing is everything. A great offer sent during a peak moment can feel disruptive. But the same offer sent when engagement dips can bring a fan back into the experience.

Here, we can see live events flowing through the real-time intelligence layer.

Fabric Eventstream ingests fan engagement events, point-of-sale transactions, crowd density readings, and game context. Those events land in Eventhouse, where KQL queries detect changes in behavior within seconds.

In this example, SportsIQ identifies a fan whose engagement score is dropping. The fan has been away from their seat longer than expected, has not interacted with the app recently, and is near a concession zone.

That combination creates a high-value intervention opportunity.

Raw signals alone are not enough. SportsIQ enriches each event with context from Microsoft Fabric and OneLake.

The system joins the live signal with FanProfile, SeatZone, EngagementPattern, PromotionHistory, and GameContext data. It checks loyalty tier, average spend, preferred sections, historical purchase behavior, churn risk, previous offer response, and current game conditions.

Most importantly, SportsIQ scopes identity using both fan ID and game ID, so recommendations stay tied to the current live session.

Now the reasoning layer takes over.

A Fabric Data Agent evaluates whether this is true disengagement or simply normal movement around the arena. Then a Foundry workflow decides whether to act, suppress, or escalate.

The workflow checks offer fatigue rules before recommending anything. If the fan recently received an offer, SportsIQ avoids sending another one too soon. If the game excitement score spikes, the system suppresses the offer because the fan is likely re-engaged by the action on the court.

In this case, the timing is right. The fan is disengaged, near concessions, and historically responds well to food and beverage promotions.

For higher-value or sensitive campaigns, SportsIQ can route the recommendation through a human-in-the-loop approval step.

The operations team sees the recommended action, the reason behind it, expected revenue impact, and the guardrails that were applied. This makes the AI decision transparent and auditable.

The approver can accept, modify, or reject the recommendation. Once approved, the action moves to the delivery layer.

The fan receives a personalized in-game offer through the mobile app.

Instead of a generic discount, the message is contextual: it reflects the fan's location, timing, loyalty profile, and current game moment. For example, SportsIQ might send a limited-time concession voucher that is easy to redeem nearby before the next possession sequence.

The objective is not just to push promotions. It is to deliver the right action, to the right fan, at the right moment.

After the offer is delivered, SportsIQ does not stop there.

The response event flows back into the real-time stream. If the fan redeems the offer, returns to their seat, opens the app, or ignores the message, that outcome becomes part of the feedback loop.

This closed-loop design allows the system to continuously improve fan models, promotion strategy, and timing rules across the season.

Finally, the operations view shows measurable impact.

Teams can monitor engagement recovery, offer conversion, incremental spend, approval latency, delivery performance, and agent telemetry. This gives business, operations, and technical teams a shared view of what happened and why.

SportsIQ brings together Microsoft Fabric, real-time intelligence, Fabric IQ, Foundry agents, human approval, and personalized fan activation into one end-to-end system.

That is SportsIQ: real-time fan intelligence, AI-powered decisioning, and closed-loop revenue optimization for the live game experience.

---

## Optional SSML Structure

Use this structure if your Foundry Speech workflow supports SSML. Keep the exact script above as the source text, then add short breaks between scenes.

```xml
<speak version="1.0" xml:lang="en-US">
  <voice name="en-US-JennyNeural">
    <prosody rate="-2%" pitch="+0%">
      Welcome to SportsIQ, an AI-powered fan engagement and revenue optimization platform for live sports venues.
      <break time="500ms"/>
      In this demo, we will see how SportsIQ detects real-time fan behavior during an professional basketball game, enriches it with business context, reasons over engagement patterns, recommends the right intervention, and closes the loop with measurable feedback.
      <break time="700ms"/>
      Continue with the remaining copy-paste script, adding 400 to 700 millisecond breaks between major scenes.
    </prosody>
  </voice>
</speak>
```

---

## Editing Notes

| Need | Recommended Treatment |
|---|---|
| Screen is ahead of narration | Freeze the frame briefly or add a slow zoom. |
| Narration is ahead of screen | Trim cursor movement and transition time. |
| A UI detail is hard to see | Add a callout box or 120-140% zoom. |
| Demo feels too long | Remove one sentence from context enrichment and one sentence from feedback. |
| Demo feels too fast | Add 300-500 ms pauses after each scene title or visual transition. |
| Final export | MP4, 1080p, 30 fps, captions enabled. |

