// ============================================================
// GapAnalysisEngine — checks debt, emergency fund, tax setup
// Runs BEFORE any portfolio recommendation
// ============================================================

import { UserProfile, Debt } from "../models/UserProfile";

export type GapSeverity = "critical" | "high" | "medium" | "low";

export interface Gap {
  id: string;
  severity: GapSeverity;
  title: string;
  description: string;
  action: string;
  blocksInvesting: boolean;
  estimatedImpact?: string;       // e.g. "Costs you €600/year"
}

export interface GapAnalysisResult {
  uid: string;
  analyzedAt: string;
  gaps: Gap[];
  criticalGaps: Gap[];
  investingBlocked: boolean;
  blockingReason?: string;
  monthlyInvestableSurplus: number;
  recommendedEmergencyFundTarget: number;
  currentEmergencyFundMonths: number;
  readinessScore: number;
  summary: string;
}

export class GapAnalysisEngine {

  analyze(profile: UserProfile): GapAnalysisResult {
    const gaps: Gap[] = [];

    // --- 1. EMERGENCY FUND CHECK ---
    const minMonths = 3;
    const recommendedMonths = 6;
    const emergencyTarget = profile.monthlyExpenses * recommendedMonths;

    if (profile.emergencyFundMonths < minMonths) {
      gaps.push({
        id: "EMERGENCY_FUND_CRITICAL",
        severity: "critical",
        title: "Emergency fund below minimum",
        description: `You have ${profile.emergencyFundMonths.toFixed(1)} months covered. Minimum is 3 months (€${(profile.monthlyExpenses * 3).toLocaleString("de-DE")}).`,
        action: `Build emergency fund to €${(profile.monthlyExpenses * 3).toLocaleString("de-DE")} before investing. Use ING Tagesgeld or Trade Republic Savings (3%+ p.a.)`,
        blocksInvesting: true,
        estimatedImpact: "Without emergency fund, you'd sell investments at worst time"
      });
    } else if (profile.emergencyFundMonths < recommendedMonths) {
      gaps.push({
        id: "EMERGENCY_FUND_LOW",
        severity: "medium",
        title: "Emergency fund below recommended 6 months",
        description: `You have ${profile.emergencyFundMonths.toFixed(1)} months. Recommended: 6 months (€${emergencyTarget.toLocaleString("de-DE")}).`,
        action: "Build to 6 months while investing. Split surplus 50/50 until reached.",
        blocksInvesting: false
      });
    }

    // --- 2. HIGH-INTEREST DEBT CHECK ---
    const highInterestThreshold = 5.0; // %
    const mustClearDebts = profile.debts.filter(
      (d) => d.interestRate > highInterestThreshold && d.amountEur > 100
    );

    mustClearDebts.forEach((debt) => {
      const annualInterestCost = debt.amountEur * (debt.interestRate / 100);
      gaps.push({
        id: `HIGH_INTEREST_DEBT_${debt.name.toUpperCase().replace(/\s/g, "_")}`,
        severity: "critical",
        title: `High-interest debt: ${debt.name}`,
        description: `${debt.name} at ${debt.interestRate}% costs €${annualInterestCost.toFixed(0)}/year. Any ETF needs to beat ${debt.interestRate}% guaranteed — it cannot.`,
        action: `Clear this debt FIRST. Guaranteed ${debt.interestRate}% return beats any ETF after tax.`,
        blocksInvesting: debt.interestRate > 10,
        estimatedImpact: `Paying off saves €${annualInterestCost.toFixed(0)}/year guaranteed`
      });
    });

    // --- 3. LOW-YIELD CASH DRAG ---
    const scalableTagesgeld = profile.assets.find(
      (a) => a.name.toLowerCase().includes("scalable") && a.type === "tagesgeld"
    );
    if (scalableTagesgeld && (scalableTagesgeld.interestRate ?? 0) < 3.0) {
      const annualLoss = scalableTagesgeld.valueEur * (3.0 - (scalableTagesgeld.interestRate ?? 0)) / 100;
      gaps.push({
        id: "LOW_YIELD_TAGESGELD",
        severity: "high",
        title: `Tagesgeld earning ${scalableTagesgeld.interestRate ?? 0}% — below market rate`,
        description: `€${scalableTagesgeld.valueEur.toLocaleString("de-DE")} at ${scalableTagesgeld.interestRate ?? 0}% when Trade Republic pays 3.25%. Lost opportunity: ~€${annualLoss.toFixed(0)}/year.`,
        action: "Move excess cash (beyond 6-month emergency fund) to Trade Republic Savings (3.25%) or invest in portfolio.",
        blocksInvesting: false,
        estimatedImpact: `€${annualLoss.toFixed(0)}/year in forgone interest`
      });
    }

    // --- 4. BAV CHECK ---
    if (profile.tax.bav === null) {
      gaps.push({
        id: "BAV_UNKNOWN",
        severity: "high",
        title: "bAV (employer pension) status unknown",
        description: "Luxoft may match bAV contributions. Unchecked = potentially free money uncollected.",
        action: "Check payslip for 'AG-Anteil bAV' or 'Direktversicherung'. Ask HR if Luxoft offers employer-matched bAV.",
        blocksInvesting: false,
        estimatedImpact: "Employer match of €100/month = €1,200/year free + tax savings"
      });
    }

    // --- 5. REVOLUT RATE UNKNOWN ---
    const revolutAsset = profile.assets.find(
      (a) => a.name.toLowerCase().includes("revolut")
    );
    if (revolutAsset && !revolutAsset.interestRate) {
      gaps.push({
        id: "REVOLUT_RATE_UNKNOWN",
        severity: "low",
        title: "Revolut savings rate not confirmed",
        description: `€${revolutAsset.valueEur.toLocaleString("de-DE")} in Revolut at unknown rate. May be earning below 3%.`,
        action: "Check Revolut app for current savings rate. If below 3%, move to Trade Republic Savings.",
        blocksInvesting: false
      });
    }

    // --- 6. FREISTELLUNGSAUFTRAG ---
    if (profile.tax.freistellungsauftrag < 2000 && profile.maritalStatus === "married") {
      gaps.push({
        id: "FREISTELLUNGSAUFTRAG_LOW",
        severity: "medium",
        title: "Freistellungsauftrag below €2,000 married allowance",
        description: `Married couples can exempt €2,000/year. You have €${profile.tax.freistellungsauftrag} set.`,
        action: "Update Freistellungsauftrag to €2,000 with Scalable Capital immediately.",
        blocksInvesting: false,
        estimatedImpact: "Up to €500/year in unnecessary tax"
      });
    }

    // --- 7. OVER-ALLOCATION TO CASH ---
    const sixMonthTarget = profile.monthlyExpenses * 6;
    const excessCash = profile.liquidAssets - sixMonthTarget;
    if (excessCash > 10000) {
      gaps.push({
        id: "EXCESS_CASH",
        severity: "high",
        title: `€${excessCash.toLocaleString("de-DE")} excess cash not working for you`,
        description: `After 6-month emergency fund (€${sixMonthTarget.toLocaleString("de-DE")}), you have €${excessCash.toLocaleString("de-DE")} idle. Real return ≈ 0% after inflation.`,
        action: "Deploy excess cash into portfolio via lump sum OR save as house down payment fund — not let it sit idle.",
        blocksInvesting: false,
        estimatedImpact: `€${Math.round(excessCash * 0.05).toLocaleString("de-DE")}/year in missed returns (5% assumed)`
      });
    }

    // --- 8. INDIAN PF PENDING ---
    if (profile.tax.indianPfPending) {
      gaps.push({
        id: "INDIAN_PF_TAX",
        severity: "low",
        title: "Indian PF withdrawal — German tax declaration needed",
        description: "PF withdrawal may be taxable in Germany under India-Germany DTAA. Don't assume it's exempt.",
        action: "In the year you withdraw: declare on Anlage KAP in Steuererklärung. Consult Steuerberater for the exact DTAA treatment.",
        blocksInvesting: false
      });
    }

    // --- COMPUTE FINAL RESULT ---
    const criticalGaps = gaps.filter((g) => g.severity === "critical");
    const investingBlocked = gaps.some((g) => g.blocksInvesting);

    // Monthly investable surplus (after mandatory savings/debt payments)
    const mandatoryDebtPayments = profile.debts
      .filter((d) => d.monthlyPayment && d.amountEur > 100)
      .reduce((sum, d) => sum + (d.monthlyPayment ?? 0), 0);
    const monthlyInvestableSurplus = Math.max(0, profile.monthlySurplus - mandatoryDebtPayments);

    // Readiness score (0–100)
    let score = 100;
    gaps.forEach((g) => {
      if (g.severity === "critical") score -= 20;
      else if (g.severity === "high") score -= 10;
      else if (g.severity === "medium") score -= 5;
      else score -= 2;
    });
    score = Math.max(0, Math.min(100, score));

    const summary = this.buildSummary(gaps, investingBlocked, monthlyInvestableSurplus);

    return {
      uid: profile.uid,
      analyzedAt: new Date().toISOString(),
      gaps,
      criticalGaps,
      investingBlocked,
      blockingReason: investingBlocked ? criticalGaps.map((g) => g.title).join("; ") : undefined,
      monthlyInvestableSurplus,
      recommendedEmergencyFundTarget: emergencyTarget,
      currentEmergencyFundMonths: profile.emergencyFundMonths,
      readinessScore: score,
      summary
    };
  }

  private buildSummary(gaps: Gap[], blocked: boolean, surplus: number): string {
    if (blocked) {
      return `⛔ Investing BLOCKED. Resolve critical gaps first: ${gaps.filter(g => g.blocksInvesting).map(g => g.title).join(", ")}.`;
    }
    if (gaps.length === 0) {
      return `✅ No gaps found. Ready to invest €${surplus.toLocaleString("de-DE")}/month.`;
    }
    const critical = gaps.filter(g => g.severity === "critical").length;
    const high = gaps.filter(g => g.severity === "high").length;
    return `⚠️ ${gaps.length} gap(s) found (${critical} critical, ${high} high priority). Investing possible but address gaps to optimise returns. Monthly investable surplus: €${surplus.toLocaleString("de-DE")}.`;
  }
}
