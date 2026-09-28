# Sports-IQ Architecture
### A simple view of the sports data, AI agents, and business actions that work together

Sports-IQ helps sports organizations turn live fan signals into timely, relevant engagement. The team brings the data and connects the channels; the Sports-IQ harness provides the intelligence, decisioning, and orchestration.

---

## How It Works

```mermaid
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
    'lineColor':'#FFC107',
  'secondaryColor':'#BAE1FF',
    'tertiaryColor':'#FFFFFF',
    'background':'#FFFFFF',
    'mainBkg':'#FFFFFF',
    'nodeBkg':'#FFFFFF',
    'nodeBorder':'#374151',
    'nodeTextColor':'#111827',
    'clusterBkg':'#FFFFFF',
    'clusterBorder':'#6B7280',
    'edgeLabelBackground':'#FFFFFF'
}}}%%
flowchart LR
  LEGEND_GREEN["Green\nSports team sources and capabilities"]
  LEGEND_BLUE["Blue\nSports-IQ assets and harness OOTB"]
  LEGEND_YELLOW["Yellow\nSports Team owned guardrails and configurability"]

  subgraph SOURCES["Sports Team Data Sources"]
    direction TB
    REALTIME["Realtime game moments and venue signals\nScore | period | timeout | possession\nCrowd energy | noise | density | weather\nIn-arena movement | Wi-Fi | camera or IoT signals"]
    HISTORICAL["Historical fan and business history\nFan profile | loyalty | consent | preferences\nPurchase history | tickets | attendance\nOffers | redemptions | engagement history"]
    SEMANTIC["Semantic model and business context\nClean definitions for fan, game, venue, and offer\nTrusted relationships across team data\nShared measures and KPIs"]
  end

  subgraph EXTENSIBILITY["Team Configuration and Extensibility"]
    direction TB
    COPILOT["Executive Visibility - \nTeams Agents | M365 Agents\nTeam workflows and experiences"]
    GUARDRAILS["Guardrail skills - \nSafety | consent | fatigue | brand policy"]
    RULES["Business rule skills - \nEligibility | budgets | offers | KPIs"]
    KNOWLEDGE["Org knowledge - \nVenue guides | playbooks | FAQs | policies"]
    TOOLS["First- and third-party MCP tools\nTicketing | POS | CRM | messaging\nVenue systems | external services"]
  end

  subgraph HARNESS["Sports-IQ Agentic Harness"]
    direction TB
    CONTEXT["Intelligent Context Agent\nCombines live signals, fan history,\nand game context into one view"]
    MONITOR["Engagement Monitor Agent\nIdentifies changes in fan interest,\nintent, and opportunity"]
    GENERATOR["Offer Generator Agent\nCreates the right offer, message,\nand timing for the moment"]
    APPROVER["Offer Approver Agent\nApplies business rules, brand policy,\nbudget, and approval requirements"]
  end

  CHANNELS["Connected action channels\nMobile app | SMS | Email\nTeams | POS | Digital signage"]
  OUTCOMES["Business outcomes\nMore relevant fan engagement\nPersonalized offers and experiences\nMeasured redemption and response\nContinuous improvement"]

  REALTIME -->|"Read live moments"| MONITOR
  HISTORICAL --> CONTEXT
  SEMANTIC --> CONTEXT
  KNOWLEDGE -->|"Ground context"| CONTEXT
  COPILOT -->|"Extend team experiences"| GENERATOR
  GUARDRAILS --> APPROVER
  RULES --> APPROVER
  TOOLS -->|"Connect approved tools"| GENERATOR
  CONTEXT --> MONITOR
  MONITOR --> GENERATOR
  GENERATOR --> APPROVER
  APPROVER -->|"Deliver approved experiences"| CHANNELS
  CHANNELS -->|"Capture response and outcomes"| OUTCOMES
  OUTCOMES -.->|"Improve future decisions"| CONTEXT

    classDef team fill:#DDEFE1,color:#173B1D,stroke:#65A66F,stroke-width:2px
    classDef harness fill:#DCEBFA,color:#12304A,stroke:#5B9BD5,stroke-width:2px
    classDef outcome fill:#FFF0C2,color:#4A3900,stroke:#D6A900,stroke-width:2px
    classDef legendGreen fill:#DDEFE1,color:#173B1D,stroke:#65A66F,stroke-width:1px,rx:12,ry:12
    classDef legendBlue fill:#DCEBFA,color:#12304A,stroke:#5B9BD5,stroke-width:1px,rx:12,ry:12
    classDef legendYellow fill:#FFF0C2,color:#4A3900,stroke:#D6A900,stroke-width:1px,rx:12,ry:12

    style SOURCES fill:#F4FAF5,stroke:#2E7D32,stroke-width:2px,color:#111827
    style EXTENSIBILITY fill:#FFF9E6,stroke:#B8860B,stroke-width:2px,color:#111827
    style HARNESS fill:#F3F8FD,stroke:#2F75B5,stroke-width:2px,color:#111827
    style OUTCOMES fill:#FFF9E6,stroke:#B8860B,stroke-width:2px,color:#111827

    linkStyle default stroke:#FFC107,stroke-width:2px

    class REALTIME,HISTORICAL,SEMANTIC,CHANNELS team
    class COPILOT,GUARDRAILS,RULES,KNOWLEDGE,TOOLS team
    class CONTEXT,MONITOR,GENERATOR,APPROVER harness
    class OUTCOMES outcome
    class LEGEND_GREEN legendGreen
    class LEGEND_BLUE legendBlue
    class LEGEND_YELLOW legendYellow
```

**Color key:** Green = sports team inputs and channels | Blue = Sports-IQ agents and orchestration | Yellow = business outcomes and learning

---

## Responsibility Matrix

| Area | Sports team brings and connects | Sports-IQ harness provides | Result for the business |
|---|---|---|---|
| **Fan identity and profile** | Fan ID, loyalty tier, consent, preferences, and relevant history | Creates a usable fan context across systems | More relevant experiences for each fan |
| **Attendance and ticketing** | Ticket purchase, entry, seat or section, membership, and suite information | Connects the fan to the current game and location | Better timing and audience selection |
| **Purchases and commerce** | POS transactions, product catalog, concession locations, and redemption data | Finds opportunities and measures response | Increased conversion and revenue insight |
| **Digital engagement** | App events, web activity, message responses, and channel preferences | Detects changes in interest and intent | Timely engagement without guesswork |
| **Game and venue context** | Score, period, timeout, game state, crowd, and venue signals | Understands the moment before recommending action | Offers that fit what is happening now |
| **Unstructured knowledge** | Venue guides, playbooks, policies, documents, FAQs, and other approved content | Grounds context and recommendations in team knowledge | More useful, explainable decisions |
| **Skills and governance** | Configurable skills, prompts, policies, approvals, budgets, and Copilot workflows | Connects team configuration directly to the agentic harness | Governed intelligence that reflects team priorities |
| **MCP tools and services** | First- and third-party tools for ticketing, POS, CRM, messaging, venue systems, and external services | Connects tools to the right agent and action | More automation across the existing ecosystem |
| **Offers and business rules** | Offer catalog, budgets, eligibility, brand policy, and approval contacts | Generates, checks, and routes recommendations | Controlled personalization at scale |
| **Delivery channels** | Access to mobile app, messaging, POS, Teams, or signage endpoints | Orchestrates approved actions through the right channel | A connected fan engagement workflow |
| **Feedback and measurement** | Redemption, dismissal, opt-out, revenue, and campaign outcomes | Feeds results back into future recommendations | A measurable, continuously improving program |

---

## The Agent Team at a Glance

| Agent or tool | Plain-language responsibility |
|---|---|
| **Intelligent Context Agent** | Brings the relevant fan, game, and business information together from realtime, historical and semantic sources. |
| **Engagement Monitor Agent** | Watches for meaningful changes in fan interest or behavior. |
| **Offer Generator Agent** | Recommends what to say, what to offer, and when to act. |
| **Offer Approver Agent** | Ensures every action follows business, brand, budget, and approval rules. |
| **Connected action channels** | Deliver the approved experience and return the response. |

---

## What a Sports Team Needs to Bring

Start with the data and channels that are available today. A useful first connection typically includes:

- A way to identify a fan or audience, with the required consent and privacy controls
- Current game, attendance, ticketing, or venue context
- Purchase or redemption history, if offers or commerce are in scope
- At least one engagement signal, such as app activity, messaging response, or attendance behavior
- An offer catalog and the business rules that govern eligibility, budget, brand, and approval
- One delivery channel and a way to capture the outcome

The harness can expand as more sources become available. The core pattern remains simple: **connect the signal, understand the moment, make a governed decision, act, and learn from the response.**

---

