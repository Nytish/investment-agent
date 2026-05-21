// ============================================================
// Agent Tools — Gemini function declarations + executors
// Each tool: declaration (for Gemini) + executor (your code)
// ============================================================

import { FunctionDeclaration, SchemaType } from "@google/generative-ai";
import { getUserProfile, savePortfolio, saveNotification } from "../services/FirestoreService";
import { GapAnalysisEngine } from "../engines/GapAnalysisEngine";
import { PortfolioEngine } from "../engines/PortfolioEngine";
import { MonteCarloEngine } from "../engines/MonteCarloEngine";
import { TaxEngine } from "../engines/TaxEngine";
import { NITISH_UID, NITISH_PROFILE } from "../services/SeedData";
import { Portfolio } from "../models/Portfolio";
import { Notification, NotificationType } from "../models/Notification";
import crypto from "crypto";

const gapEngine = new GapAnalysisEngine();
const portfolioEngine = new PortfolioEngine();
const monteCarloEngine = new MonteCarloEngine();
const taxEngine = new TaxEngine();

// ── Tool declarations (sent to Gemini) ───────────────────────

export const TOOL_DECLARATIONS: FunctionDeclaration[] = [
  {
    name: "getFinancialProfile",
    description: "Get Nitish's complete financial profile including assets, debts, goals, risk profile, and tax setup from the database.",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {},
      required: []
    }
  },
  {
    name: "runGapAnalysis",
    description: "Analyse Nitish's financial situation for critical gaps: emergency fund status, high-interest debts, cash drag, tax setup, bAV. Always run this before portfolio recommendations.",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {},
      required: []
    }
  },
  {
    name: "generatePortfolioOptions",
    description: "Generate Conservative, Balanced, and Growth portfolio options with specific ETF recommendations (ISIN, TER, allocations) tailored to Nitish's risk profile and goals.",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {
        monthlyInvestment: {
          type: SchemaType.NUMBER,
          description: "Monthly amount to invest in EUR. Use profile surplus if not specified."
        }
      },
      required: ["monthlyInvestment"]
    }
  },
  {
    name: "runMonteCarlo",
    description: "Calculate probability of reaching FIRE goal (€600,000 by age 47) using 1000 Monte Carlo simulations. Shows pessimistic/median/optimistic scenarios and sensitivity to contribution changes.",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {
        monthlyContribution: {
          type: SchemaType.NUMBER,
          description: "Monthly investment amount in EUR"
        },
        startingCapital: {
          type: SchemaType.NUMBER,
          description: "Starting investable capital in EUR (default: current investable assets)"
        },
        targetAmount: {
          type: SchemaType.NUMBER,
          description: "Target portfolio amount in EUR (default: 600000 for FIRE)"
        },
        years: {
          type: SchemaType.NUMBER,
          description: "Investment horizon in years (default: 13 for FIRE at 47)"
        },
        expectedReturn: {
          type: SchemaType.NUMBER,
          description: "Expected annual return % (default: 7.0 for balanced portfolio)"
        }
      },
      required: []
    }
  },
  {
    name: "calculateVorabpauschale",
    description: "Calculate German Vorabpauschale tax for accumulating ETFs. Shows exact formula, Basiszins, Teilfreistellung, and total tax due in January.",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {
        fundValueStartOfYear: {
          type: SchemaType.NUMBER,
          description: "ETF/fund value at start of year (1 January) in EUR"
        },
        fundValueEndOfYear: {
          type: SchemaType.NUMBER,
          description: "ETF/fund value at end of year (31 December) in EUR"
        },
        distributionsReceived: {
          type: SchemaType.NUMBER,
          description: "Dividends or distributions received during the year in EUR (0 for accumulating ETFs)"
        },
        isEquityFund: {
          type: SchemaType.BOOLEAN,
          description: "True for MSCI World/EM ETFs (30% Teilfreistellung)"
        },
        year: {
          type: SchemaType.NUMBER,
          description: "Tax year (e.g. 2026)"
        }
      },
      required: ["fundValueStartOfYear", "fundValueEndOfYear", "isEquityFund", "year"]
    }
  },
  {
    name: "calculateAfterTaxReturn",
    description: "Calculate the real after-tax return for different asset classes in Germany (equity ETF, gold, bonds, Tagesgeld). Shows effective tax rate and net return.",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {
        grossReturnPercent: {
          type: SchemaType.NUMBER,
          description: "Gross annual return before tax in %"
        },
        assetClass: {
          type: SchemaType.STRING,
          description: "Asset class: equity_etf | bond_etf | reit_etf | gold | tagesgeld | individual_stock"
        },
        holdingYears: {
          type: SchemaType.NUMBER,
          description: "Number of years held (important for gold 1yr tax-free rule)"
        }
      },
      required: ["grossReturnPercent", "assetClass"]
    }
  },
  {
    name: "checkRebalancing",
    description: "Check if Nitish's current portfolio has drifted from target allocations and needs rebalancing. Shows drift per asset class and recommended buy/sell amounts.",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {
        currentHoldings: {
          type: SchemaType.STRING,
          description: "JSON string of current holdings with values in EUR, e.g. [{name:'VWCE',value:5000},{name:'EUWAX Gold II',value:4712}]"
        }
      },
      required: ["currentHoldings"]
    }
  },
  {
    name: "calculateFreistellungsauftrag",
    description: "Track Freistellungsauftrag usage (€2,000 annual tax-free allowance for married couple). Shows how much is used, remaining, and tax saved.",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {
        tagesgeldInterestEur: {
          type: SchemaType.NUMBER,
          description: "Interest earned on Tagesgeld/savings this year in EUR"
        },
        etfGainsEur: {
          type: SchemaType.NUMBER,
          description: "Realised ETF gains this year in EUR (0 if no sales)"
        },
        dividendsEur: {
          type: SchemaType.NUMBER,
          description: "Dividends received this year in EUR (0 for accumulating ETFs)"
        }
      },
      required: ["tagesgeldInterestEur"]
    }
  },
  {
    name: "logNotification",
    description: "Log a notification to Firestore for Nitish to review (rebalance alert, tax reminder, goal milestone, etc.)",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {
        type: {
          type: SchemaType.STRING,
          description: "Notification type: NT01_REBALANCE_ALERT | NT02_CONTRIBUTION_REMINDER | NT03_MARKET_DROP_ALERT | NT04_TAX_DEADLINE | NT05_VORABPAUSCHALE_NOTICE | NT06_WEEKLY_INSIGHT | NT07_GOAL_MILESTONE"
        },
        title: {
          type: SchemaType.STRING,
          description: "Short notification title"
        },
        body: {
          type: SchemaType.STRING,
          description: "Notification body message"
        },
        actionLabel: {
          type: SchemaType.STRING,
          description: "Action button label, e.g. 'Rebalance now'"
        }
      },
      required: ["type", "title", "body", "actionLabel"]
    }
  }
];

// ── Tool executors (your code runs these) ─────────────────────

export async function executeTool(name: string, args: Record<string, unknown>): Promise<unknown> {
  switch (name) {

    case "getFinancialProfile": {
      const profile = await getUserProfile(NITISH_UID);
      return profile ?? NITISH_PROFILE; // fallback to seed data if Firestore not yet seeded
    }

    case "runGapAnalysis": {
      const profile = await getUserProfile(NITISH_UID) ?? NITISH_PROFILE;
      const result = gapEngine.analyze(profile);
      return result;
    }

    case "generatePortfolioOptions": {
      const profile = await getUserProfile(NITISH_UID) ?? NITISH_PROFILE;
      const monthly = (args.monthlyInvestment as number) ?? 1000;
      const result = portfolioEngine.generate(profile, monthly);
      return result;
    }

    case "runMonteCarlo": {
      const profile = await getUserProfile(NITISH_UID) ?? NITISH_PROFILE;
      const result = monteCarloEngine.run({
        startingCapital: (args.startingCapital as number) ?? 20000,
        monthlyContribution: (args.monthlyContribution as number) ?? 1000,
        targetAmount: (args.targetAmount as number) ?? 600000,
        years: (args.years as number) ?? 13,
        expectedAnnualReturn: (args.expectedReturn as number) ?? 7.0,
        annualReturnStdDev: 15.0,    // MSCI World historical std dev
        annualInflation: 2.3,         // Germany current
        simulations: 1000
      });
      return result;
    }

    case "calculateVorabpauschale": {
      const result = taxEngine.calculateVorabpauschale({
        fundValueStartOfYear: (args.fundValueStartOfYear as number),
        fundValueEndOfYear: (args.fundValueEndOfYear as number),
        distributionsReceived: (args.distributionsReceived as number) ?? 0,
        isEquityFund: (args.isEquityFund as boolean) ?? true,
        isMixedFund: false,
        isRealEstateFund: false,
        year: (args.year as number) ?? new Date().getFullYear()
      });
      return result;
    }

    case "calculateAfterTaxReturn": {
      const result = taxEngine.calculateAfterTaxReturn({
        grossReturnPercent: (args.grossReturnPercent as number),
        assetClass: (args.assetClass as "equity_etf" | "bond_etf" | "reit_etf" | "gold" | "tagesgeld" | "individual_stock"),
        holdingYears: (args.holdingYears as number) ?? undefined,
        freistellungsauftragRemaining: 2000
      });
      return result;
    }

    case "checkRebalancing": {
      try {
        const holdings = JSON.parse(args.currentHoldings as string);
        const totalValue = holdings.reduce((sum: number, h: { value: number }) => sum + h.value, 0);

        // Target: balanced portfolio
        const targets: Record<string, number> = {
          "VWCE": 55,
          "IS3N": 15,
          "EUWAX Gold II": 10,
          "IWDP": 10,
          "Cash": 10
        };

        const drifts = holdings.map((h: { name: string; value: number }) => {
          const currentPercent = (h.value / totalValue) * 100;
          const targetPercent = targets[h.name] ?? 0;
          const drift = currentPercent - targetPercent;
          return {
            name: h.name,
            currentPercent: Math.round(currentPercent * 10) / 10,
            targetPercent,
            driftPercent: Math.round(drift * 10) / 10,
            action: drift > 5 ? "SELL" : drift < -5 ? "BUY" : "HOLD",
            actionAmountEur: Math.round(Math.abs(drift / 100) * totalValue)
          };
        });

        const needsRebalancing = drifts.some((d: { driftPercent: number }) => Math.abs(d.driftPercent) > 5);
        return {
          needsRebalancing,
          totalPortfolioValue: totalValue,
          drifts,
          message: needsRebalancing
            ? "Portfolio needs rebalancing. Review drifts above 5%."
            : "Portfolio within target bands. No rebalancing needed."
        };
      } catch {
        return { error: "Invalid holdings format. Provide JSON array: [{name:'VWCE',value:5000}]" };
      }
    }

    case "calculateFreistellungsauftrag": {
      const result = taxEngine.calculateFreistellungsauftragUsage(
        (args.tagesgeldInterestEur as number) ?? 0,
        (args.etfGainsEur as number) ?? 0,
        (args.dividendsEur as number) ?? 0,
        2000 // married couple limit
      );
      return result;
    }

    case "logNotification": {
      const notification: Notification = {
        id: crypto.randomUUID(),
        uid: NITISH_UID,
        type: (args.type as NotificationType),
        title: args.title as string,
        body: args.body as string,
        actionLabel: args.actionLabel as string,
        actionRoute: "/notifications",
        status: "pending",
        createdAt: new Date().toISOString()
      };
      await saveNotification(notification);
      return { success: true, notificationId: notification.id, message: "Notification logged." };
    }

    default:
      return { error: `Unknown tool: ${name}` };
  }
}
