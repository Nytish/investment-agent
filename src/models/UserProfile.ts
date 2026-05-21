// ============================================================
// UserProfile — Financial DNA model
// Stores complete onboarding data for the investment agent
// ============================================================

export type MaritalStatus = "single" | "married" | "divorced";
export type ResidencyStatus = "work_visa" | "niederlassungserlaubnis" | "eu_citizen" | "german_citizen";
export type RiskReaction = "a_panic_sell" | "b_hold_stressed" | "c_hold_calm" | "d_buy_more";
export type AutomationLevel = "a_fully_automated" | "b_alert_confirm" | "c_manual";
export type InvestmentStyle = "passive" | "hybrid" | "active";
export type KnowledgeLevel = "beginner" | "intermediate" | "advanced";
export type GoalType = "FIRE" | "house" | "wealth" | "retirement" | "education" | "business";

export interface Asset {
  name: string;
  type: "tagesgeld" | "giro" | "etp" | "etf" | "stock" | "crypto" | "real_estate" | "foreign_cash" | "pension";
  value: number;                // EUR
  currency: string;             // EUR, INR, etc.
  valueEur: number;             // always in EUR
  interestRate?: number;        // annual %, e.g. 2.0
  broker?: string;
  isin?: string;
  purchaseDate?: string;        // ISO date
  taxFreeAfter?: string;        // ISO date — for gold/crypto 1yr rule
  notes?: string;
}

export interface Debt {
  name: string;
  type: "credit_card" | "student_loan" | "car_loan" | "mortgage" | "personal_loan" | "other";
  amount: number;               // EUR
  currency: string;
  amountEur: number;
  interestRate: number;         // annual %
  monthlyPayment?: number;
  dueDate?: string;             // final payment date
  country: string;
  priority: "must_clear" | "monitor" | "ignore"; // set by gap analysis
}

export interface FinancialGoal {
  type: GoalType;
  description: string;
  targetAmount?: number;        // EUR
  targetYear?: number;
  targetAge?: number;
  priority: "primary" | "secondary" | "tertiary";
}

export interface TaxProfile {
  freistellungsauftrag: number;          // EUR, e.g. 2000 for married
  steuerklasse: string;                  // "III", "IV", etc.
  filesSteuererklarung: boolean;
  steuererklarungYears: number[];        // years already filed
  bav: boolean | null;                   // null = unknown
  bavMonthlyAmount?: number;             // EUR/month employer contributes
  niederlassungserlaubnis: boolean;
  residencyPermitValidUntil?: string;
  indianPfPending: boolean;
  indianPfAmountInr?: number;
  foreignIncome: boolean;
}

export interface UserProfile {
  uid: string;

  // Personal
  firstName: string;
  lastName: string;
  email: string;
  dateOfBirth: string;              // "1991-07-26"
  age: number;
  maritalStatus: MaritalStatus;
  children: number;
  residencyStatus: ResidencyStatus;
  country: string;                  // "DE"
  city: string;                     // "Ingolstadt"
  employer: string;

  // Monthly cashflow
  monthlyNetIncome: number;         // 4315.34
  monthlyKindergeld: number;        // 255
  monthlyElterngeld: number;        // if applicable
  monthlySpouseIncome: number;      // 0 (homemaker)
  totalMonthlyIncome: number;       // calculated
  monthlyExpenses: number;          // 1760
  monthlySurplus: number;           // calculated

  // Assets & debts
  assets: Asset[];
  debts: Debt[];
  totalAssets: number;              // sum of all valueEur
  totalDebts: number;               // sum of all amountEur
  netWorth: number;                 // totalAssets - totalDebts
  liquidAssets: number;             // cash + tagesgeld + savings
  emergencyFundMonths: number;      // liquid / monthlyExpenses

  // Goals
  goals: FinancialGoal[];
  fireTargetAge: number;            // 47
  fireTargetYear: number;           // 2039
  fireNumber: number;               // €600,000 (4% rule target)

  // Risk & preferences
  riskReaction: RiskReaction;
  automationLevel: AutomationLevel;
  investmentStyle: InvestmentStyle;
  knowledgeLevel: KnowledgeLevel;
  hoursPerMonthForReview: number;
  riskScore: number;                // 0–100

  // Tax
  tax: TaxProfile;

  // Meta
  readinessScore: number;           // 71
  onboardingCompleted: boolean;
  createdAt: string;
  updatedAt: string;
}
