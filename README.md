# AI Investment Agent

> Personal AI Investment Co-pilot for Nitish Bidwe — Ingolstadt, Bavaria

![TypeScript](https://img.shields.io/badge/TypeScript-5.4-blue) ![Node](https://img.shields.io/badge/Node-20%2B-green) ![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange) ![Firebase](https://img.shields.io/badge/Firebase-Firestore-yellow)

---

## Features

- Conversational portfolio management via CLI or Web UI
- Portfolio gap analysis against target allocation (80% ETF core / 20% satellite)
- FIRE planning with Monte Carlo simulation (target: €600k by age 47)
- German tax corner: Vorabpauschale calculator, Freistellungsauftrag tracker, Elster guide
- Rebalancing alerts with drift detection per holding
- Scheduled Cloud Function notifications (tax deadlines, rebalancing, Vorabpauschale)
- Persistent holdings and insights stored in Firebase Firestore

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/Nytish/investment-agent.git
cd investment-agent
npm install

# 2. Configure environment
cp .env.example .env
# Edit .env — fill in GEMINI_API_KEY and FIREBASE_PROJECT_ID

# 3. Launch
npm run serve        # Web UI at http://localhost:3000
# or
npm start            # CLI mode
```

---

## Commands

| Command              | Description                           |
|----------------------|---------------------------------------|
| `npm start`          | Interactive CLI agent session         |
| `npm run serve`      | Web UI server on localhost:3000       |
| `npm run build`      | Compile TypeScript to dist/           |
| `npm run typecheck`  | Type-check without emitting files     |

---

## Tool Inventory (19 tools)

### Portfolio & Analysis

| Tool                       | Description                                       |
|----------------------------|---------------------------------------------------|
| `getFinancialProfile`      | Return Nitish's full financial DNA snapshot       |
| `runGapAnalysis`           | Compare current allocation to target, flag gaps   |
| `generatePortfolioOptions` | Suggest ETF/asset options to fill identified gaps |
| `runMonteCarlo`            | Simulate FIRE scenarios (1000+ runs)              |
| `checkRebalancing`         | Detect drift in holdings vs. target weights       |
| `calculateAfterTaxReturn`  | Net return after Abgeltungsteuer + Soli           |

### Holdings

| Tool                   | Description                             |
|------------------------|-----------------------------------------|
| `getPortfolioHoldings` | Fetch all holdings from Firestore       |
| `addPortfolioHolding`  | Add a new holding with value and ticker |
| `updateHoldingValue`   | Update current market value of holding  |
| `deleteHolding`        | Remove a holding from the portfolio     |

### Insights

| Tool                    | Description                                       |
|-------------------------|---------------------------------------------------|
| `generateWeeklyInsight` | Generate and persist a weekly portfolio insight   |
| `getLatestInsight`      | Retrieve the most recent stored insight           |

### Notifications

| Tool                       | Description                                |
|----------------------------|--------------------------------------------|
| `getNotifications`         | List pending notifications                 |
| `markNotificationRead`     | Mark a notification as read               |
| `getNotificationSettings`  | Retrieve user notification preferences    |
| `logNotification`          | Write a new notification to Firestore     |

### German Tax Corner

| Tool                            | Description                                        |
|---------------------------------|----------------------------------------------------|
| `calculateVorabpauschale`       | Compute annual prepaid capital gains tax           |
| `calculateFreistellungsauftrag` | Track FSA usage against €1,000 allowance           |
| `getTaxDeadlines`               | List relevant German tax deadlines for the year    |
| `getElsterGuide`                | Step-by-step Elster filing instructions            |
| `getTaxYearSummary`             | Full tax summary for a given calendar year         |

---

## Architecture

```
  CLI (npm start)          Web UI (npm run serve)
       |                          |
       +-----------+--------------+
                   |
           InvestmentAgent
           (Gemini 2.5 Flash)
                   |
     +-------------+-------------+
     |             |             |
 HoldingTools  InsightTools  TaxTools
 NotifTools    PortfolioTools
     |             |             |
     +-------------+-------------+
                   |
         +---------+---------+
         |      Engines       |
         |  MonteCarloEngine  |
         |  GapAnalysisEngine |
         |  PortfolioEngine   |
         |  TaxEngine         |
         +--------+-----------+
                  |
         +--------+-----------+
         |   Firebase          |
         |   Firestore         |
         |  (holdings,         |
         |   insights,         |
         |   notifications)    |
         +--------------------+
                  ^
         Cloud Functions
         (scheduled notifications:
          rebalancing, Vorabpauschale,
          tax deadlines, weekly insight)
```

---

## German Tax Features

| Feature                   | Detail                                                         |
|---------------------------|----------------------------------------------------------------|
| Vorabpauschale            | Annual calculation based on Basiszins + fund value             |
| Freistellungsauftrag      | Tracks usage of the €1,000/year tax-free allowance             |
| Abgeltungsteuer           | 25% flat tax + 5.5% Soli surcharge on capital gains            |
| Elster guide              | Step-by-step instructions for KAP Anlage (investment income)   |
| Tax year summary          | Aggregated view of gains, FSA consumed, tax owed               |
| Deadline reminders        | Automated Cloud Function alerts for key German tax dates       |

---

## Deploy Scheduled Notifications

```bash
cd functions
npm install
npm run build
firebase deploy --only functions
```

Scheduled triggers:
- 3rd of month, 9 AM — monthly contribution reminder
- July 1st, 9 AM — tax deadline alert (30 days before July 31)
- January 1st, 8 AM — Vorabpauschale notice
- Every Monday, 9 AM — weekly portfolio insight

---

## Security

- `.env` is listed in `.gitignore` and must **never** be committed
- This agent is built for **personal use only** — no multi-user auth
- Firebase service account JSON (if used) must also be excluded from git
- See `.env.example` for the full list of required variables

---

## Links

- GitHub: [https://github.com/Nytish/investment-agent](https://github.com/Nytish/investment-agent)
- Gemini API keys: [aistudio.google.com](https://aistudio.google.com)
- Firebase console: [console.firebase.google.com](https://console.firebase.google.com)
