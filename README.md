# AI Investment Co-pilot

Personal AI financial agent for Nitish Bidwe.
Built on: Gemini 2.0 Flash + Firebase + TypeScript.

---

## Quick Start

### 1. Set up Firebase credentials (one-time)

Option A — Application Default Credentials (recommended):
```bash
gcloud auth application-default login
```

Option B — Service account key:
- Go to: Firebase Console → Project Settings → Service Accounts
- Click "Generate new private key" → download JSON
- Save as `serviceAccount.json` in project root
- Uncomment `FIREBASE_SERVICE_ACCOUNT_PATH` in `.env`

### 2. Deploy Firestore rules (one-time)
```bash
firebase login
firebase use financialaiagent-809ee
firebase deploy --only firestore:rules
```

### 3. Start the agent
```bash
npm start
```

---

## Example questions

```
"What should I invest this month?"
"Am I on track for FIRE at 47?"
"Should I rebalance my portfolio?"
"What's my Vorabpauschale for 2026?"
"How much do I save in tax with accumulating vs distributing ETFs?"
"Compare VWCE vs IWDA+IS3N split"
"How long until I hit 25% of my FIRE goal?"
"What happens if markets drop 30% next year?"
```

---

## Project structure

```
src/
  index.ts                  ← CLI entry point (npm start)
  agent/
    InvestmentAgent.ts      ← Gemini tool-calling loop
    tools.ts                ← 9 financial tools (declarations + executors)
    prompts.ts              ← System prompt with full Financial DNA
  engines/
    GapAnalysisEngine.ts    ← Debt, emergency fund, tax gap checks
    PortfolioEngine.ts      ← Conservative/Balanced/Growth allocations
    MonteCarloEngine.ts     ← 1000-simulation probability calculator
    TaxEngine.ts            ← Vorabpauschale, Freistellungsauftrag
  models/
    UserProfile.ts          ← Financial DNA types
    Portfolio.ts            ← Portfolio + ETF catalogue types
    Notification.ts         ← 7 notification types
  services/
    FirestoreService.ts     ← Firestore CRUD
    SeedData.ts             ← Pre-populated Financial DNA (onboarding data)
  notifications/
    NotificationTriggers.ts ← 7 notification generators

functions/                  ← Firebase Cloud Functions (scheduled notifications)
  src/index.ts              ← 4 scheduled triggers (monthly, tax, weekly)
```

---

## Deploy scheduled notifications

```bash
cd functions
npm install
npm run build
firebase deploy --only functions
```

Scheduled triggers:
- 3rd of month, 9AM → contribution reminder
- July 1st, 9AM → tax deadline (30 days before July 31)
- January 1st, 8AM → Vorabpauschale notice
- Every Monday, 9AM → weekly insight

---

## Environment variables (.env)

```
GEMINI_API_KEY=           ← from aistudio.google.com
FIREBASE_PROJECT_ID=financialaiagent-809ee
FIREBASE_SERVICE_ACCOUNT_PATH=./serviceAccount.json  ← optional
AGENT_ENV=development
AGENT_USER_ID=nitish_bidwe
```

---

## Update your financial data

Edit `src/services/SeedData.ts` when:
- Salary changes
- New assets added
- Goals change
- bAV confirmed

Then re-run `npm start` — agent fetches latest from Firestore.
