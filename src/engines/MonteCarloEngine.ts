// ============================================================
// MonteCarloEngine — probability of reaching financial goals
// Uses 1000 simulations with randomised annual returns
// Shows math: formula visible in every result
// ============================================================

export interface MonteCarloInput {
  startingCapital: number;        // EUR — investable today
  monthlyContribution: number;    // EUR/month
  targetAmount: number;           // EUR — FIRE number or goal
  years: number;                  // investment horizon
  expectedAnnualReturn: number;   // % e.g. 7.0
  annualReturnStdDev: number;     // % e.g. 15.0 (MSCI World historical)
  annualInflation: number;        // % e.g. 2.3
  simulations?: number;           // default 1000
}

export interface ScenarioResult {
  label: string;
  percentile: number;             // e.g. 50 = median
  finalPortfolioValue: number;    // EUR nominal
  finalPortfolioRealValue: number; // EUR inflation-adjusted
  achieved: boolean;
  shortfallOrSurplus: number;     // EUR (negative = shortfall)
}

export interface MonteCarloResult {
  input: MonteCarloInput;
  probabilityOfSuccess: number;   // % — scenarios that hit target
  scenarios: {
    pessimistic: ScenarioResult;  // 25th percentile
    median: ScenarioResult;       // 50th percentile
    optimistic: ScenarioResult;   // 75th percentile
    worstCase: ScenarioResult;    // 5th percentile
  };
  sensitivityAnalysis: SensitivityRow[];
  formula: string;
  keyInsights: string[];
  analyzedAt: string;
}

export interface SensitivityRow {
  label: string;
  monthlyContribution: number;
  probabilityOfSuccess: number;
  finalValueMedian: number;
}

export class MonteCarloEngine {

  run(input: MonteCarloInput): MonteCarloResult {
    const {
      startingCapital,
      monthlyContribution,
      targetAmount,
      years,
      expectedAnnualReturn,
      annualReturnStdDev,
      annualInflation,
      simulations = 1000
    } = input;

    const monthlyRate = expectedAnnualReturn / 100 / 12;
    const months = years * 12;
    const results: number[] = [];

    // Run simulations
    for (let sim = 0; sim < simulations; sim++) {
      let portfolio = startingCapital;

      for (let month = 0; month < months; month++) {
        // Random annual return (Box-Muller normal distribution)
        const annualReturn = this.randomNormal(expectedAnnualReturn, annualReturnStdDev);
        const mRate = (annualReturn / 100) / 12;
        portfolio = portfolio * (1 + mRate) + monthlyContribution;
      }

      results.push(portfolio);
    }

    results.sort((a, b) => a - b);

    const successCount = results.filter((r) => r >= targetAmount).length;
    const probabilityOfSuccess = (successCount / simulations) * 100;

    // Percentile helper
    const percentileValue = (p: number): number => {
      const idx = Math.floor((p / 100) * simulations);
      return results[Math.min(idx, simulations - 1)];
    };

    const inflationFactor = Math.pow(1 + annualInflation / 100, years);
    const buildScenario = (label: string, percentile: number): ScenarioResult => {
      const nominal = percentileValue(percentile);
      const real = nominal / inflationFactor;
      return {
        label,
        percentile,
        finalPortfolioValue: Math.round(nominal),
        finalPortfolioRealValue: Math.round(real),
        achieved: nominal >= targetAmount,
        shortfallOrSurplus: Math.round(nominal - targetAmount)
      };
    };

    const scenarios = {
      worstCase: buildScenario("Worst Case (5th percentile)", 5),
      pessimistic: buildScenario("Pessimistic (25th percentile)", 25),
      median: buildScenario("Median (50th percentile)", 50),
      optimistic: buildScenario("Optimistic (75th percentile)", 75)
    };

    // Sensitivity analysis — effect of contributing more
    const sensitivitySteps = [-200, 0, 200, 500];
    const sensitivityAnalysis: SensitivityRow[] = sensitivitySteps.map((delta) => {
      const contrib = Math.max(0, monthlyContribution + delta);
      const simResults: number[] = [];

      for (let sim = 0; sim < 500; sim++) {
        let portfolio = startingCapital;
        for (let month = 0; month < months; month++) {
          const annualReturn = this.randomNormal(expectedAnnualReturn, annualReturnStdDev);
          const mRate = (annualReturn / 100) / 12;
          portfolio = portfolio * (1 + mRate) + contrib;
        }
        simResults.push(portfolio);
      }

      simResults.sort((a, b) => a - b);
      const successRate = (simResults.filter((r) => r >= targetAmount).length / 500) * 100;
      const median = simResults[Math.floor(simResults.length / 2)];

      const label = delta === 0
        ? `Base: €${contrib.toLocaleString("de-DE")}/month`
        : delta > 0
          ? `+€${delta} more: €${contrib.toLocaleString("de-DE")}/month`
          : `-€${Math.abs(delta)} less: €${contrib.toLocaleString("de-DE")}/month`;

      return {
        label,
        monthlyContribution: contrib,
        probabilityOfSuccess: Math.round(successRate),
        finalValueMedian: Math.round(median)
      };
    });

    const formula = `
FORMULA USED:
─────────────────────────────────────────────────────
Portfolio(t+1) = Portfolio(t) × (1 + r_monthly) + C

Where:
  r_monthly = random_normal(μ=${expectedAnnualReturn}%, σ=${annualReturnStdDev}%) ÷ 12
  C         = €${monthlyContribution.toLocaleString("de-DE")}/month contribution
  Simulations: ${simulations}
  Horizon:    ${years} years (${months} months)
  Target:     €${targetAmount.toLocaleString("de-DE")}
  Inflation:  ${annualInflation}% p.a. (for real value)

Return assumption based on MSCI World 40-year annualised returns.
─────────────────────────────────────────────────────`;

    const keyInsights = this.generateInsights(
      probabilityOfSuccess,
      scenarios,
      sensitivityAnalysis,
      targetAmount,
      years
    );

    return {
      input,
      probabilityOfSuccess: Math.round(probabilityOfSuccess),
      scenarios,
      sensitivityAnalysis,
      formula,
      keyInsights,
      analyzedAt: new Date().toISOString()
    };
  }

  private randomNormal(mean: number, stdDev: number): number {
    // Box-Muller transform
    const u1 = Math.random();
    const u2 = Math.random();
    const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    return mean + stdDev * z;
  }

  private generateInsights(
    probability: number,
    scenarios: MonteCarloResult["scenarios"],
    sensitivity: SensitivityRow[],
    target: number,
    years: number
  ): string[] {
    const insights: string[] = [];

    // Probability framing
    if (probability >= 80) {
      insights.push(`✅ ${Math.round(probability)}% probability of success — strong plan. Stay the course.`);
    } else if (probability >= 60) {
      insights.push(`🟡 ${Math.round(probability)}% probability — good but not comfortable. Consider increasing contributions.`);
    } else if (probability >= 40) {
      insights.push(`⚠️ ${Math.round(probability)}% probability — coin-flip territory. Significant plan adjustment needed.`);
    } else {
      insights.push(`🔴 ${Math.round(probability)}% probability — plan needs major revision. Either extend timeline or increase contributions.`);
    }

    // Worst case
    if (scenarios.worstCase.shortfallOrSurplus < 0) {
      insights.push(`In 5% of scenarios (severe bear market), portfolio reaches €${scenarios.worstCase.finalPortfolioValue.toLocaleString("de-DE")} — shortfall of €${Math.abs(scenarios.worstCase.shortfallOrSurplus).toLocaleString("de-DE")}.`);
    }

    // Median shortfall or surplus
    if (scenarios.median.achieved) {
      insights.push(`Median scenario: €${scenarios.median.finalPortfolioValue.toLocaleString("de-DE")} — €${scenarios.median.shortfallOrSurplus.toLocaleString("de-DE")} above target.`);
    } else {
      insights.push(`Median scenario falls €${Math.abs(scenarios.median.shortfallOrSurplus).toLocaleString("de-DE")} SHORT of target. Increase contributions or extend timeline.`);
    }

    // Sensitivity — most impactful row
    const baseContrib = sensitivity[1]?.monthlyContribution ?? 0;
    const bestBoost = sensitivity.find((s) => s.monthlyContribution > baseContrib);
    if (bestBoost) {
      const baseProbability = sensitivity.find((s) => s.label.startsWith("Base"))?.probabilityOfSuccess ?? probability;
      const boost = bestBoost.probabilityOfSuccess - baseProbability;
      if (boost > 5) {
        insights.push(`Investing €${bestBoost.monthlyContribution.toLocaleString("de-DE")}/month raises probability by +${boost}% to ${bestBoost.probabilityOfSuccess}%.`);
      }
    }

    // Real value warning
    insights.push(`After ${years} years at 2.3% inflation, €${target.toLocaleString("de-DE")} today = €${Math.round(target * Math.pow(1.023, years)).toLocaleString("de-DE")} in future money. Plan adjusts for this.`);

    return insights;
  }
}
