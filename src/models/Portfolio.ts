// ============================================================
// Portfolio — allocation model + holding types
// ============================================================

export type PortfolioStyle = "conservative" | "balanced" | "growth";
export type AssetClass = "world_etf" | "em_etf" | "bonds" | "gold" | "reit" | "crypto" | "cash" | "individual_stock";

export interface ETFRecommendation {
  name: string;
  isin: string;
  ticker: string;
  ter: number;                    // Total Expense Ratio, e.g. 0.0022
  domicile: string;               // "IE" = Ireland (UCITS)
  accumulating: boolean;          // true = thesaurierend (no dividend payout)
  ucits: boolean;
  exchange: string;               // "XETRA", "LSE", etc.
  currency: string;               // "EUR"
  trackingIndex: string;
  vorabpauschaleApplies: boolean;
  teilfreistellung: number;       // 0.3 = 30% for equity ETFs
  notes?: string;
}

export interface TargetAllocation {
  assetClass: AssetClass;
  label: string;
  percentage: number;             // 0–100
  etf?: ETFRecommendation;
  riskLevel: "low" | "medium" | "high";
  rebalanceThreshold: number;     // drift % that triggers rebalance alert, e.g. 5
}

export interface MonthlyContributionPlan {
  totalMonthlyInvestment: number;
  houseSavingsMonthly: number;
  portfolioInvestmentMonthly: number;
  cashBufferMonthly: number;
  allocationBreakdown: {
    assetClass: AssetClass;
    label: string;
    monthlyAmount: number;
    etfName?: string;
    isin?: string;
  }[];
}

export interface Holding {
  id: string;
  name: string;
  assetClass: AssetClass;
  isin?: string;
  broker: string;
  units?: number;
  currentPrice?: number;          // EUR per unit
  currentValue: number;           // EUR
  purchaseDate?: string;
  avgPurchasePrice?: number;      // EUR per unit
  unrealizedGain?: number;        // EUR
  unrealizedGainPercent?: number;
  taxFreeAfter?: string;          // for gold/crypto 1yr rule
  notes?: string;
}

export interface Portfolio {
  uid: string;
  style: PortfolioStyle;
  targetAllocations: TargetAllocation[];
  currentHoldings: Holding[];
  totalPortfolioValue: number;    // EUR
  monthlyContributionPlan: MonthlyContributionPlan;
  benchmarkIndex: string;         // "MSCI World"
  lastRebalanceDate?: string;
  lastUpdated: string;
  createdAt: string;
}

export interface RebalanceResult {
  needsRebalancing: boolean;
  drifts: {
    assetClass: AssetClass;
    label: string;
    targetPercent: number;
    currentPercent: number;
    driftPercent: number;         // positive = overweight, negative = underweight
    actionRequired: "buy" | "sell" | "hold";
    actionAmountEur: number;
    etfName?: string;
    isin?: string;
  }[];
  summary: string;
}

// ETF catalogue — UCITS, Ireland-domiciled, recommended for Germany-based investor
export const ETF_CATALOGUE: Record<string, ETFRecommendation> = {
  VWCE: {
    name: "Vanguard FTSE All-World UCITS ETF (Acc)",
    isin: "IE00BK5BQT80",
    ticker: "VWCE",
    ter: 0.0022,
    domicile: "IE",
    accumulating: true,
    ucits: true,
    exchange: "XETRA",
    currency: "EUR",
    trackingIndex: "FTSE All-World",
    vorabpauschaleApplies: true,
    teilfreistellung: 0.3,
    notes: "Best single-fund world solution. Includes EM (10%). No separate EM needed."
  },
  IWDA: {
    name: "iShares Core MSCI World UCITS ETF (Acc)",
    isin: "IE00B4L5Y983",
    ticker: "IWDA",
    ter: 0.002,
    domicile: "IE",
    accumulating: true,
    ucits: true,
    exchange: "XETRA",
    currency: "EUR",
    trackingIndex: "MSCI World",
    vorabpauschaleApplies: true,
    teilfreistellung: 0.3,
    notes: "Developed markets only. Pair with IS3N for EM exposure."
  },
  IS3N: {
    name: "iShares Core MSCI EM IMI UCITS ETF (Acc)",
    isin: "IE00BKM4GZ66",
    ticker: "IS3N",
    ter: 0.0018,
    domicile: "IE",
    accumulating: true,
    ucits: true,
    exchange: "XETRA",
    currency: "EUR",
    trackingIndex: "MSCI EM IMI",
    vorabpauschaleApplies: true,
    teilfreistellung: 0.3,
    notes: "Includes small caps (IMI). Lowest TER in EM space."
  },
  IEAG: {
    name: "iShares Core Euro Govt Bond UCITS ETF (Dist)",
    isin: "IE00B4WXJJ64",
    ticker: "IEAG",
    ter: 0.0007,
    domicile: "IE",
    accumulating: false,
    ucits: true,
    exchange: "XETRA",
    currency: "EUR",
    trackingIndex: "Bloomberg Euro Government Bond",
    vorabpauschaleApplies: false,
    teilfreistellung: 0,
    notes: "Euro govt bonds only. Low TER. Only use if risk score < 40."
  },
  IWDP: {
    name: "iShares Developed Markets Property Yield UCITS ETF",
    isin: "IE00B1FZS350",
    ticker: "IWDP",
    ter: 0.0059,
    domicile: "IE",
    accumulating: false,
    ucits: true,
    exchange: "XETRA",
    currency: "EUR",
    trackingIndex: "FTSE EPRA/NAREIT Developed Dividend+",
    vorabpauschaleApplies: false,
    teilfreistellung: 0,
    notes: "REIT exposure. Higher TER. Use for real estate diversification."
  },
  EUWAX_GOLD_II: {
    name: "EUWAX Gold II",
    isin: "DE000EWG2LD7",
    ticker: "EWG2",
    ter: 0,
    domicile: "DE",
    accumulating: false,
    ucits: false,
    exchange: "EUWAX",
    currency: "EUR",
    trackingIndex: "Gold (physically backed)",
    vorabpauschaleApplies: false,
    teilfreistellung: 0,
    notes: "Tax-free gains after 1 year holding (§23 EStG). Already held. Keep."
  }
};
