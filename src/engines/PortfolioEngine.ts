// ============================================================
// PortfolioEngine — generates 3 portfolio options
// Conservative / Balanced / Growth
// All ETFs: UCITS, Ireland-domiciled, EUR-denominated
// ============================================================

import { UserProfile } from "../models/UserProfile";
import {
  Portfolio,
  PortfolioStyle,
  TargetAllocation,
  MonthlyContributionPlan,
  ETF_CATALOGUE,
} from "../models/Portfolio";

export interface PortfolioRecommendation {
  style: PortfolioStyle;
  label: string;
  description: string;
  targetAllocations: TargetAllocation[];
  monthlyContributionPlan: MonthlyContributionPlan;
  expectedAnnualReturn: number;       // %
  expectedVolatility: number;         // % std dev
  worstYearDrawdown: number;          // % historical worst
  recoveryYears: number;              // avg years to recover from worst
  suitableFor: string;
  warnings: string[];
}

export class PortfolioEngine {

  generate(profile: UserProfile, monthlyInvestment: number): {
    conservative: PortfolioRecommendation;
    balanced: PortfolioRecommendation;
    growth: PortfolioRecommendation;
    recommended: PortfolioStyle;
    recommendedReason: string;
  } {
    const conservative = this.buildConservative(profile, monthlyInvestment);
    const balanced = this.buildBalanced(profile, monthlyInvestment);
    const growth = this.buildGrowth(profile, monthlyInvestment);

    const { recommended, reason } = this.pickRecommended(profile);

    return { conservative, balanced, growth, recommended, recommendedReason: reason };
  }

  private buildConservative(profile: UserProfile, monthly: number): PortfolioRecommendation {
    const allocations: TargetAllocation[] = [
      {
        assetClass: "world_etf",
        label: "FTSE All-World ETF (Developed + EM)",
        percentage: 40,
        etf: ETF_CATALOGUE["VWCE"],
        riskLevel: "medium",
        rebalanceThreshold: 5
      },
      {
        assetClass: "bonds",
        label: "Euro Government Bonds",
        percentage: 30,
        etf: ETF_CATALOGUE["IEAG"],
        riskLevel: "low",
        rebalanceThreshold: 5
      },
      {
        assetClass: "gold",
        label: "Physical Gold ETP (tax-free after 1yr)",
        percentage: 15,
        etf: ETF_CATALOGUE["EUWAX_GOLD_II"],
        riskLevel: "medium",
        rebalanceThreshold: 5
      },
      {
        assetClass: "cash",
        label: "High-yield Savings (Trade Republic 3.25%)",
        percentage: 15,
        riskLevel: "low",
        rebalanceThreshold: 5
      }
    ];

    return {
      style: "conservative",
      label: "Conservative",
      description: "Capital preservation with modest growth. Heavy bonds + cash. Suitable if sleep > returns.",
      targetAllocations: allocations,
      monthlyContributionPlan: this.buildContributionPlan(monthly, allocations),
      expectedAnnualReturn: 4.5,
      expectedVolatility: 8,
      worstYearDrawdown: -12,
      recoveryYears: 2,
      suitableFor: "Risk score < 40, short horizon (< 5 years), or near retirement",
      warnings: [
        "Bonds underperform stocks over 15+ year horizons",
        "At 4.5% return, €600k FIRE target harder to reach by 47",
        "For 13-year FIRE horizon, this portfolio likely falls short"
      ]
    };
  }

  private buildBalanced(profile: UserProfile, monthly: number): PortfolioRecommendation {
    const allocations: TargetAllocation[] = [
      {
        assetClass: "world_etf",
        label: "FTSE All-World ETF (Core — 70% of equity)",
        percentage: 55,
        etf: ETF_CATALOGUE["VWCE"],
        riskLevel: "medium",
        rebalanceThreshold: 5
      },
      {
        assetClass: "em_etf",
        label: "MSCI EM IMI ETF (Satellite — EM tilt)",
        percentage: 15,
        etf: ETF_CATALOGUE["IS3N"],
        riskLevel: "high",
        rebalanceThreshold: 5
      },
      {
        assetClass: "gold",
        label: "Physical Gold ETP (tax-free after 1yr)",
        percentage: 10,
        etf: ETF_CATALOGUE["EUWAX_GOLD_II"],
        riskLevel: "medium",
        rebalanceThreshold: 5
      },
      {
        assetClass: "reit",
        label: "Developed Markets REIT ETF",
        percentage: 10,
        etf: ETF_CATALOGUE["IWDP"],
        riskLevel: "medium",
        rebalanceThreshold: 5
      },
      {
        assetClass: "cash",
        label: "High-yield Savings (emergency + buffer)",
        percentage: 10,
        riskLevel: "low",
        rebalanceThreshold: 5
      }
    ];

    return {
      style: "balanced",
      label: "Balanced (Recommended for you)",
      description: "Core-satellite hybrid. 70% global equity + 15% EM tilt + gold/REIT diversifiers. Matches your hybrid style preference.",
      targetAllocations: allocations,
      monthlyContributionPlan: this.buildContributionPlan(monthly, allocations),
      expectedAnnualReturn: 7.0,
      expectedVolatility: 14,
      worstYearDrawdown: -30,
      recoveryYears: 3,
      suitableFor: "Risk score 40–70, 10–20 year horizon, hybrid style preference",
      warnings: [
        "30% worst-year drawdown will test your (b) risk reaction — prepare mentally",
        "REIT ETF has higher TER (0.59%) — review if real estate exposure truly needed",
        "EM allocation adds volatility — acceptable at 15%"
      ]
    };
  }

  private buildGrowth(profile: UserProfile, monthly: number): PortfolioRecommendation {
    const allocations: TargetAllocation[] = [
      {
        assetClass: "world_etf",
        label: "FTSE All-World ETF (Core)",
        percentage: 60,
        etf: ETF_CATALOGUE["VWCE"],
        riskLevel: "medium",
        rebalanceThreshold: 5
      },
      {
        assetClass: "em_etf",
        label: "MSCI EM IMI ETF (EM overweight)",
        percentage: 25,
        etf: ETF_CATALOGUE["IS3N"],
        riskLevel: "high",
        rebalanceThreshold: 5
      },
      {
        assetClass: "gold",
        label: "Physical Gold ETP",
        percentage: 5,
        etf: ETF_CATALOGUE["EUWAX_GOLD_II"],
        riskLevel: "medium",
        rebalanceThreshold: 7
      },
      {
        assetClass: "reit",
        label: "Developed Markets REIT ETF",
        percentage: 5,
        etf: ETF_CATALOGUE["IWDP"],
        riskLevel: "medium",
        rebalanceThreshold: 7
      },
      {
        assetClass: "individual_stock",
        label: "Individual stocks / thematic (satellite picks)",
        percentage: 5,
        riskLevel: "high",
        rebalanceThreshold: 10
      }
    ];

    return {
      style: "growth",
      label: "Growth",
      description: "Maximum long-term growth. 85% equity-heavy. High volatility. Only if you can stomach -40% years.",
      targetAllocations: allocations,
      monthlyContributionPlan: this.buildContributionPlan(monthly, allocations),
      expectedAnnualReturn: 9.0,
      expectedVolatility: 20,
      worstYearDrawdown: -45,
      recoveryYears: 5,
      suitableFor: "Risk score > 70, 15+ year horizon, (c) or (d) drop reaction",
      warnings: [
        "⚠️ You rated (b) for drop reaction. Growth portfolio will cause real stress in bear markets.",
        "25% EM is aggressive — EM has underperformed developed markets for 15+ years",
        "Individual stock picking consistently underperforms index funds for retail investors",
        "NOT recommended for your current risk profile"
      ]
    };
  }

  private buildContributionPlan(monthly: number, allocations: TargetAllocation[]): MonthlyContributionPlan {
    const breakdown = allocations.map((a) => ({
      assetClass: a.assetClass,
      label: a.label,
      monthlyAmount: Math.round((monthly * a.percentage) / 100),
      etfName: a.etf?.name,
      isin: a.etf?.isin
    }));

    return {
      totalMonthlyInvestment: monthly,
      houseSavingsMonthly: 0,       // set externally based on goal
      portfolioInvestmentMonthly: monthly,
      cashBufferMonthly: 0,
      allocationBreakdown: breakdown
    };
  }

  private pickRecommended(profile: UserProfile): { recommended: PortfolioStyle; reason: string } {
    const reaction = profile.riskReaction;
    const score = profile.riskScore;
    const style = profile.investmentStyle;

    if (reaction === "a_panic_sell" || score < 30) {
      return {
        recommended: "conservative",
        reason: "Low risk tolerance + panic sell reaction → conservative protects capital"
      };
    }

    if (reaction === "c_hold_calm" || reaction === "d_buy_more" || score > 70) {
      return {
        recommended: "growth",
        reason: "High risk tolerance + buy-the-dip reaction → growth maximises long-term returns"
      };
    }

    return {
      recommended: "balanced",
      reason: `(b) hold-but-stressed reaction + hybrid style preference + 13-year FIRE horizon → balanced maximises return per unit of stress`
    };
  }
}
