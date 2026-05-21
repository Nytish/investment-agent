// ============================================================
// SeedData — Nitish's complete Financial DNA
// Pre-populated from Phase 0 onboarding interview
// Run once on first launch to initialise Firestore
// ============================================================

import { UserProfile } from "../models/UserProfile";
import { NotificationSettings } from "../models/Notification";

export const NITISH_UID = process.env.AGENT_USER_ID ?? "nitish_bidwe";

export const NITISH_PROFILE: UserProfile = {
  uid: NITISH_UID,

  // Personal
  firstName: "Nitish",
  lastName: "Bidwe",
  email: "ntshbidwe@gmail.com",
  dateOfBirth: "1991-07-26",
  age: 34,
  maritalStatus: "married",
  children: 1,
  residencyStatus: "niederlassungserlaubnis",
  country: "DE",
  city: "Ingolstadt",
  employer: "Luxoft",

  // Monthly cashflow
  monthlyNetIncome: 4315.34,
  monthlyKindergeld: 255.00,
  monthlyElterngeld: 0,           // confirm actual amount
  monthlySpouseIncome: 0,         // homemaker
  totalMonthlyIncome: 4570.34,
  monthlyExpenses: 1760.00,
  monthlySurplus: 2810.34,        // includes Kindergeld

  // Assets
  assets: [
    {
      name: "Scalable Capital Tagesgeldkonto",
      type: "tagesgeld",
      value: 30785.71,
      currency: "EUR",
      valueEur: 30785.71,
      interestRate: 2.0,
      broker: "Scalable Capital",
      notes: "Emergency fund + excess cash. Rate below market — address in gap analysis."
    },
    {
      name: "EUWAX Gold II",
      type: "etp",
      value: 4712.00,
      currency: "EUR",
      valueEur: 4712.00,
      broker: "Scalable Capital",
      isin: "DE000EWG2LD7",
      taxFreeAfter: "2025-01-01",   // update with actual purchase date + 1yr
      notes: "Intentional gold hedge. Tax-free after 1 year (§23 EStG). Keep."
    },
    {
      name: "Scalable Capital Cash Section",
      type: "giro",
      value: 1700.00,
      currency: "EUR",
      valueEur: 1700.00,
      broker: "Scalable Capital",
      notes: "Uninvested cash in brokerage account"
    },
    {
      name: "German Salary Account",
      type: "giro",
      value: 3905.00,
      currency: "EUR",
      valueEur: 3905.00,
      notes: "Primary bank account for salary"
    },
    {
      name: "Revolut Savings",
      type: "tagesgeld",
      value: 10401.00,
      currency: "EUR",
      valueEur: 10401.00,
      broker: "Revolut",
      notes: "Rate unknown — verify in app. Move if < 3%."
    },
    {
      name: "HDFC Bank India",
      type: "foreign_cash",
      value: 106437,
      currency: "INR",
      valueEur: 1160.00,           // at ~91.7 INR/EUR
      notes: "Indian savings. Interest income technically declarable in Germany. Keep as India buffer."
    }
  ],

  // Debts
  debts: [
    {
      name: "Car Loan India",
      type: "car_loan",
      amount: 18673,
      currency: "INR",
      amountEur: 204,              // at ~91.7 INR/EUR
      interestRate: 0,             // last EMI only, interest negligible
      monthlyPayment: 204,
      dueDate: "2026-06-05",
      country: "IN",
      priority: "ignore"           // final payment in June, negligible
    }
  ],

  // Totals (calculated)
  totalAssets: 52663.71,
  totalDebts: 204,
  netWorth: 52459.71,
  liquidAssets: 46791.71,          // all except EUWAX Gold II
  emergencyFundMonths: 26.6,       // 46791 / 1760

  // Goals
  goals: [
    {
      type: "FIRE",
      description: "Financial Independence, Retire Early at age 47",
      targetAmount: 600000,
      targetYear: 2038,
      targetAge: 47,
      priority: "primary"
    },
    {
      type: "house",
      description: "Buy property near Ingolstadt — down payment + transaction costs",
      targetAmount: 97000,
      targetYear: 2028,
      targetAge: 37,
      priority: "secondary"
    },
    {
      type: "wealth",
      description: "Long-term wealth building alongside FIRE",
      priority: "primary"
    },
    {
      type: "business",
      description: "Future business investment (type TBD)",
      priority: "tertiary"
    }
  ],

  fireTargetAge: 47,
  fireTargetYear: 2038,
  fireNumber: 600000,              // €2,000/month expenses / 4% = €600k

  // Risk profile
  riskReaction: "b_hold_stressed",
  automationLevel: "b_alert_confirm",
  investmentStyle: "hybrid",
  knowledgeLevel: "beginner",
  hoursPerMonthForReview: 2,
  riskScore: 45,                   // moderate: (b) reaction + beginner = conservative-leaning moderate

  // Tax
  tax: {
    freistellungsauftrag: 2000,    // correctly set for married couple
    steuerklasse: "III",           // homemaker spouse
    filesSteuererklarung: true,
    steuererklarungYears: [2023, 2024],
    bav: null,                     // UNKNOWN — check payslip
    bavMonthlyAmount: undefined,
    niederlassungserlaubnis: true,
    residencyPermitValidUntil: "2035-11-30",
    indianPfPending: true,
    indianPfAmountInr: undefined,  // unknown — to be confirmed
    foreignIncome: false
  },

  readinessScore: 71,
  onboardingCompleted: true,
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString()
};

export const DEFAULT_NOTIFICATION_SETTINGS: NotificationSettings = {
  uid: NITISH_UID,
  NT01_REBALANCE_ALERT: true,
  NT02_CONTRIBUTION_REMINDER: true,
  NT03_MARKET_DROP_ALERT: true,
  NT04_TAX_DEADLINE: true,
  NT05_VORABPAUSCHALE_NOTICE: true,
  NT06_WEEKLY_INSIGHT: true,
  NT07_GOAL_MILESTONE: true,
  quietHoursStart: 22,
  quietHoursEnd: 8,
  rebalanceDriftThreshold: 5,
  contributionReminderDay: 3,
  marketDropThreshold: 10,
  updatedAt: new Date().toISOString()
};
