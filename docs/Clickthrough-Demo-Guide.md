# Sports-IQ — Clickthrough Demo Guide

> **Audience:** Business stakeholders, stadium ops leaders, Microsoft field sellers  
> **No technical setup required** — this guide walks you through the live dashboard experience  
> **Duration:** ~10 minutes for the full walkthrough

---

## What Is Sports-IQ?

Sports-IQ is an **AI-powered fan engagement platform** that turns every natural game pause — timeouts, halftimes, TV breaks — into a personalized revenue moment.

Instead of blasting generic promos to 68,000 fans at halftime, Sports-IQ:

- 📡 **Senses** live fan signals (app activity, purchases, seat location)
- 🧠 **Reasons** about each fan's engagement level, loyalty tier, and purchase history
- ⚡ **Decides** the right offer for the right fan at the right moment
- 🚦 **Requires human approval** before any offer goes out
- 📬 **Delivers** personalized offers via email, app push, or concession kiosk

> 💰 **Measured impact:** $22 uplift per fan per game · **$543K per game** · **$4.3M per season**

---

## The Dashboard at a Glance

When you open the Sports-IQ Operator Dashboard, you'll see five main areas:

```
╔══════════════════════════════════════════════════════════════╗
║  🏈 SCOREBOARD          Live game score, clock, & situation ║
╠══════════════════════════════════════════════════════════════╣
║                          ║                                  ║
║  📋 STATUS TIMELINE      ║  🤖 AGENT PIPELINE               ║
║  (left sidebar)          ║  (center — AI reasoning stream)  ║
║  Step-by-step progress   ║                                  ║
║                          ║──────────────────────────────────-║
║                          ║  🎫 APPROVAL CARD                ║
║                          ║  (appears when offer is ready)   ║
║──────────────────────────║──────────────────────────────────-║
║  👥 TRIGGERED FAN LIST   ║  🙋 FAN PROFILE CARD             ║
║  Disengaged fans found   ║  Selected fan's details           ║
║  during the game break   ║                                  ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Step-by-Step Walkthrough

### 🔧 Step 0 — Set Your Demo Email *(one-time, 30 seconds)*

Before running any offers, tell the system where to deliver approved offers.

1. Look for the **⚙ Demo** button in the top-right corner of the dashboard header
2. Click it to open the settings panel
3. Type your email address (e.g., your personal inbox or a shared demo account)
4. Click **Save**

> ✅ The email is saved in your browser and persists between page refreshes. You can change it anytime between demo runs.

---

### 🏟️ Step 1 — Simulate a Game Break *(the "trigger")*

In a real game, the system watches the live broadcast feed for natural pauses. In the demo, **you** simulate when a break happens.

1. Look at the **Scoreboard** at the top of the dashboard
   - It shows the current score: **Harbor City Comets vs Metro Stars**
   - The quarter, game clock, and game situation are displayed
2. Find the **break type dropdown** below the score
   - Options include: `Commercial`, `TV Timeout`, `Halftime`, `2-Min Warning`
3. Select a break type (recommended: **TV Timeout** for the first run)
4. Click the **▶ Simulate** button

> 🔍 **What happens behind the scenes:** The system scans all fans in the stadium and identifies those whose engagement has dropped below their tier's threshold during this game break.

---

### 👥 Step 2 — Review Triggered Fans *(~5 seconds)*

After the scan completes, the **Triggered Fan List** appears on the left side of the dashboard.

Each card shows:

| Info | What It Means |
|------|--------------|
| **Fan name** | The identified fan (e.g., "Demo Fan 001") |
| **Loyalty tier badge** | Platinum 💎 · Gold 🥇 · Silver 🥈 · Bronze 🥉 |
| **Engagement score** | How engaged they are right now (lower = more disengaged) |
| **Section** | Where they're sitting in the stadium |
| **Urgency bar** | Color-coded: 🔴 Red (very disengaged) → 🟡 Yellow (mildly) |

You can **filter** by:
- **Tier** — click a tier badge to show only Platinum fans, Gold fans, etc.
- **Section** — filter by stadium zone (Field Level, Club, Upper Deck, Merch Hub)

> 💡 **Tip:** Start with **Demo Fan 001** (Gold tier, Section S112) — he's the core demo fan with the clearest story.

---

### 🙋 Step 3 — Select a Fan to Target

1. Click on a fan card in the Triggered Fan List
2. The **Fan Profile Card** appears showing:
   - Full name and loyalty tier
   - Current section and seat location
   - Engagement score (color-coded: 🔴 red = low, 🟡 yellow = moderate, 🟢 green = high)
   - Days since last offer
3. The system immediately starts the **AI agent pipeline** for this fan

> 🎯 **What you're deciding:** "This fan is disengaged — let's see what offer the AI recommends."

---

### 🤖 Step 4 — Watch the AI Pipeline Run *(~15–30 seconds)*

The **Agent Pipeline** panel in the center of the dashboard shows the AI's work in real time. You'll see three agents fire in sequence:

#### Agent 1: 📡 Engagement Monitor
> *"Is this fan actually disengaged?"*

- Queries live engagement signals (app activity, purchase gap, dwell time)
- Returns the fan's current engagement score
- Compares against the tier-specific threshold:

| Tier | Offer triggers when score drops below |
|------|--------------------------------------|
| Platinum | 0.65 |
| Gold | 0.55 |
| Silver / Bronze | 0.45 |

#### Agent 2: ⚡ Offer Generator
> *"What's the best offer for this fan, right now?"*

- Receives enriched context: fan profile, game state, purchase history, seat location
- Applies **9 smart guardrails** (see "The Guardrails" section below)
- Selects the offer category: Food & Beverage 🍺 · Merchandise 🛍️ · Experience 🎟️
- Personalizes the copy, discount, and delivery channel

#### Agent 3: 📨 Offer Approver
> *"A human must approve before we send anything."*

- Packages the final offer and pauses for **your** approval
- The **Approval Card** appears on screen

> 📺 **What to narrate:** *"Notice how the AI is reasoning in real time — it's checking live fan signals, applying business rules, and personalizing the offer. All in under 30 seconds."*

---

### 🎫 Step 5 — Review and Approve the Offer *(the "human-in-the-loop" moment)*

The **Approval Card** appears with a category-specific header:
- 🍺 **Food & Beverage** — amber/gold accent
- 🛍️ **Merchandise** — blue/indigo accent
- 🎁 **General Offer** — neutral accent

The card shows:

| Field | Example |
|-------|---------|
| **Offer title** | "Halftime Concession Special" |
| **Description** | "15% off any food item — valid at Section S112 concession stand" |
| **Discount** | 15% off |
| **Category** | Food & Beverage |
| **Delivery channel** | Email push |

You have two choices:

#### ✅ Approve
- Click the green **Approve** button
- The offer is sent to the fan's email immediately
- A confirmation appears: *"Offer delivered via email"*
- The feedback event is logged back into the system (closed-loop design)

#### ❌ Reject
- Click the red **Reject** button
- A dropdown appears with pre-built rejection reasons:
  - *"Active stadium incident — F&B offers inappropriate"*
  - *"Offer not relevant to current game moment"*
  - *"Fan has already left the stadium"*
  - *"Other"*
- Select a reason and confirm
- The rejection is logged — the AI learns from it

> 🗣️ **Key talking point:** *"This is human-in-the-loop AI. The system recommends, but a stadium operator always has final say. No offer goes out without human approval."*

---

### 🧾 Step 6 — POS Redemption *(optional — showing the closed loop)*

After an offer is approved and delivered, the **POS Redemption Panel** appears at the bottom of the dashboard.

This simulates what happens when the fan walks up to a concession stand and scans their offer:

1. 📱 **Scanning** — The POS system reads the offer code
2. ⚡ **Eventhouse write** — The transaction is logged in real time
3. 🔄 **Lakehouse sync** — The fan's purchase history is updated
4. 🎉 **Complete** — The redemption is confirmed

Each step shows a status indicator (⏳ running → ✅ done) and latency in milliseconds.

> 💡 **Why this matters:** *"Every action feeds back into the system. The next time this fan is at a game, the AI already knows they responded to a food offer during a TV timeout. That's the learning loop."*

---

## The Guardrails — When the AI Stays Silent

One of the most powerful features of Sports-IQ is knowing **when NOT to act**. Nine guardrails protect the fan experience:

| # | Rule | What It Does |
|---|------|-------------|
| G1 | 🏈 **Scoring Zone** | Blocks all offers when the ball is near the end zone — fans are watching every play |
| G2 | 🎉 **Post-Score Window** | 60-second silence after a touchdown — fans are celebrating, not shopping |
| G3 | ⏱️ **Offer Fatigue** | Minimum gap between offers (varies by loyalty tier) — no spam |
| G4 | 💰 **Budget Cap** | Max per-fan-per-game spend — protects margins |
| G5 | 🏟️ **Critical Play** | 4th down, 2-minute drill, etc. — suppress all offers |
| G6 | 📈 **Excitement Spike** | If engagement score suddenly jumps, suppress — the fan is having a great time |
| G7 | ⭐ **Premium Window** | Pre-halftime offers reserved for Platinum/Gold fans only |
| §4.1 | 🍺 **Alcohol Policy** | Blocks alcohol offers after purchase limit is reached |
| §6 | 🚨 **Incident Proximity** | All offers blocked near an active stadium incident |

> 🗣️ **Key talking point:** *"A badly timed offer is worse than no offer at all. The AI knows when to stay silent — and that's what protects the fan experience and your brand."*

---

## Demo Fan Cheat Sheet

Use these four pre-built fans for different demo stories:

### 🥇 Demo Fan 001 — *"The Core Demo"*
| Field | Value |
|-------|-------|
| Fan ID | `bas_fan_0001` |
| Tier | Gold |
| Section | S112 (Lower Deck) |
| Engagement Score | 0.41 (triggers Gold threshold of 0.55) |
| **Story** | Core demo path — disengaged Gold fan, triggers F&B or merch offer at halftime |
| **Best for** | First-time demo, showing the full pipeline end-to-end |

### 💎 Demo Fan 002 — *"The Premium Fan"*
| Field | Value |
|-------|-------|
| Fan ID | `bas_fan_0002` |
| Tier | Platinum |
| Section | F3 (Field Level / VIP) |
| Engagement Score | 0.58 (triggers Platinum threshold of 0.65 but NOT Gold's 0.55) |
| **Story** | Premium targeting — merch and suite upgrade offers for high-value fans |
| **Best for** | Showing tier-aware logic: same score would NOT trigger for Gold fans |

### 🛍️ Demo Fan 003 — *"The Merch Zone Fan"*
| Field | Value |
|-------|-------|
| Fan ID | `bas_fan_0003` |
| Tier | Gold |
| Section | EZ5 (End Zone Merch Hub) |
| Engagement Score | 0.44 (triggers Gold threshold) |
| **Story** | Section-aware targeting — merch offers because he's near the merchandise stands |
| **Best for** | Showing location-based personalization |

### 🔄 Demo Fan 004 — *"The Churn Risk"*
| Field | Value |
|-------|-------|
| Fan ID | `bas_fan_0004` |
| Tier | Silver |
| Section | C6 (Club Level) |
| Engagement Score | 0.31 (very low — urgency) |
| **Story** | High churn risk — aggressive re-engagement with food voucher |
| **Best for** | Showing urgency-based offers and churn prevention |

---

## Suggested Demo Flow (10 Minutes)

Here's a recommended sequence for a compelling demo:

```
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
flowchart TD
    A["⚙️ Set demo email<br/><i>30 sec</i>"] --> B["🏟️ Simulate TV Timeout<br/><i>click ▶ Simulate</i>"]
    B --> C["👥 Review triggered fans<br/><i>point out scores & tiers</i>"]
    C --> D["🙋 Select Demo Fan 001<br/><i>Gold · S112 · Score 0.41</i>"]
    D --> E["🤖 Watch AI pipeline<br/><i>narrate each agent</i>"]
    E --> F["🎫 Approve the offer<br/><i>human-in-the-loop moment</i>"]
    F --> G["📬 Show email delivery<br/><i>check your inbox</i>"]
    G --> H["💎 Switch to Demo Fan 002<br/><i>show tier-aware logic</i>"]
    H --> I["🛍️ Switch to Demo Fan 003<br/><i>show section targeting</i>"]
    I --> J["📊 Recap the business case<br/><i>$22/fan · $543K/game · $4.3M/season</i>"]
```

### Minute-by-Minute Breakdown

| Time | Action | Talking Point |
|------|--------|--------------|
| **0:00–0:30** | Set demo email | *"First, I'll set where approved offers land — my inbox."* |
| **0:30–1:30** | Simulate TV Timeout, review triggered fans | *"A TV timeout just hit. The system instantly scanned 68,000 fans and found 4 who are disengaging."* |
| **1:30–2:00** | Select Demo Fan 001 | *"Marcus is a Gold tier fan in the Lower Deck. His engagement has dropped to 0.41 — below his threshold. Let's see what the AI recommends."* |
| **2:00–4:00** | Watch AI pipeline | *"Three AI agents are working in sequence: detect, reason, recommend. Watch the reasoning stream — it's checking his purchase history, seat location, and the current game state."* |
| **4:00–5:00** | Approve the offer | *"Here's the human-in-the-loop moment. The AI recommends a food offer — 15% off at his nearest concession. I approve it, and it's delivered to his phone in seconds."* |
| **5:00–6:00** | Check email delivery | *"There it is in my inbox. Personalized, contextual, and delivered during a natural game pause."* |
| **6:00–7:30** | Run pipeline for Demo Fan 002 | *"Now watch tier-aware logic. Aaliyah's a Platinum fan at 0.58 engagement. That would NOT trigger for Gold fans — but Platinum fans get earlier intervention because they're higher value."* |
| **7:30–8:30** | Run pipeline for Demo Fan 003 | *"Derek's in the Merch Hub zone. Watch how the AI picks a merchandise offer because of his seat location — that's section-aware personalization."* |
| **8:30–10:00** | Recap the business case | *"$22 uplift per fan per game. 23,800 addressable fans per game at 35% app adoption. That's $543K per game, $4.3M per season — purely from AI-timed, AI-personalized offers delivered during natural game pauses."* |

---

## Multi-Sport Capability

Sports-IQ isn't just for football. The platform supports **four sports** with a single configuration switch:

| Sport | League | Critical Moment | Break Types |
|-------|--------|----------------|-------------|
| 🏈 Football | professional football | Red Zone | Commercial, TV Timeout, Halftime, 2-Min Warning |
| 🏀 Basketball | professional basketball | Clutch Time | Timeout, TV Timeout, Halftime, End of Quarter |
| ⚽ Soccer | professional soccer | Penalty Area | Halftime, VAR Review, Injury Stoppage, Substitution |
| 🏒 Hockey | professional hockey | Power Play | TV Timeout, Intermission, Penalty, Commercial |

When the sport switches, **everything adapts automatically** — the scoreboard labels, break type options, guardrail thresholds, and offer timing rules all update to match that sport's natural rhythm.

> 🗣️ **Talking point:** *"Same platform, same AI, same dashboard — but the guardrails and timing rules are tuned to each sport's unique rhythm. A hockey power play is not the same as an professional football Red Zone drive, and Sports-IQ knows the difference."*

---

## Common Questions from the Audience

### *"How fast is it?"*
> Signal to offer in **under 10 seconds**. The AI pipeline runs during natural game pauses, so the fan receives the offer while they're already looking at their phone.

### *"What if the AI sends a bad offer?"*
> It can't — **every offer requires human approval** before delivery. The stadium operator always has final say. Plus, 9 guardrails automatically suppress offers in inappropriate moments.

### *"Does this work with our existing stadium systems?"*
> Sports-IQ integrates with existing POS systems, WiFi telemetry, and mobile apps. It's built on Microsoft Fabric (which your data team likely already uses) and Microsoft Foundry for AI reasoning.

### *"What about fan privacy?"*
> All data is first-party (fans opted in via the stadium app). No third-party data is used. The system runs entirely within your Microsoft tenant — no fan data leaves your environment.

### *"How is this different from our current marketing emails?"*
> Timing. Current marketing sends the same email to everyone after the game. Sports-IQ delivers a **personalized offer during the game**, timed to a natural pause, when the fan is most likely to act. That's the difference between a 2% redemption rate and a 15%+ rate.

### *"What's the ROI?"*
> **$22 per fan per game** uplift across 5 offer categories (F&B, Merchandise, Experiences, Fantasy, Tailgate). At 35% app adoption across 68K fans, that's **$543K per game** and **$4.3M per 8-game professional football season**.

---

## Technology Summary (for the curious)

You don't need to know any of this to run the demo, but if someone asks:

| What | Technology | Plain English |
|------|-----------|--------------|
| Data streaming | Microsoft Fabric Eventstream | Collects live fan signals from the stadium |
| Fast queries | Fabric Eventhouse (KQL) | Answers "what's happening right now?" in under half a second |
| Fan history | Fabric Lakehouse | Stores profiles, purchase history, and engagement patterns |
| AI reasoning | Microsoft Foundry (gpt-5.4) | The brain that decides what offer to send and when |
| Dashboard | Next.js web app | What you're looking at — the operator control panel |
| Delivery | Azure Communication Services | Sends the actual email/SMS to the fan |
| Infrastructure | Azure Container Apps | Runs everything in the cloud, scales automatically |

---

*Sports-IQ — Every pause is an opportunity. Every fan is unique.* 🏈🏀⚽🏒
