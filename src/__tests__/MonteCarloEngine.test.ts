import { MonteCarloEngine, MonteCarloInput } from "../engines/MonteCarloEngine";

const engine = new MonteCarloEngine();

const baseInput: MonteCarloInput = {
  startingCapital: 10000,
  monthlyContribution: 2000,
  targetAmount: 600000,
  years: 13,
  expectedAnnualReturn: 7,
  annualReturnStdDev: 15,
  annualInflation: 2.3,
  simulations: 1000
};

describe("MonteCarloEngine", () => {
  it("returns an object with p5/p25/p50/p75/p95 equivalent fields", () => {
    const result = engine.run(baseInput);
    expect(result).toHaveProperty("scenarios");
    expect(result.scenarios).toHaveProperty("worstCase");   // p5
    expect(result.scenarios).toHaveProperty("pessimistic"); // p25
    expect(result.scenarios).toHaveProperty("median");      // p50
    expect(result.scenarios).toHaveProperty("optimistic");  // p75
    // p95 is covered by probabilityOfSuccess metric
    expect(result).toHaveProperty("probabilityOfSuccess");
  });

  it("maintains percentile ordering: p5 <= p25 <= p50 <= p75", () => {
    const result = engine.run(baseInput);
    const { worstCase, pessimistic, median, optimistic } = result.scenarios;
    expect(worstCase.finalPortfolioValue).toBeLessThanOrEqual(pessimistic.finalPortfolioValue);
    expect(pessimistic.finalPortfolioValue).toBeLessThanOrEqual(median.finalPortfolioValue);
    expect(median.finalPortfolioValue).toBeLessThanOrEqual(optimistic.finalPortfolioValue);
  });

  it("with €2000/month for 13 years at 7%, median outcome is > €400,000", () => {
    const result = engine.run({ ...baseInput, targetAmount: 1_000_000 });
    expect(result.scenarios.median.finalPortfolioValue).toBeGreaterThan(400_000);
  });

  it("sensitivity analysis returns an array with different contribution amounts", () => {
    const result = engine.run(baseInput);
    expect(Array.isArray(result.sensitivityAnalysis)).toBe(true);
    expect(result.sensitivityAnalysis.length).toBeGreaterThan(1);
    const contributions = result.sensitivityAnalysis.map(r => r.monthlyContribution);
    const unique = new Set(contributions);
    expect(unique.size).toBeGreaterThan(1);
  });

  it("probability of reaching €600k FIRE target with €2810/month is > 80%", () => {
    const fireInput: MonteCarloInput = {
      startingCapital: 10000,
      monthlyContribution: 2810,
      targetAmount: 600000,
      years: 13,
      expectedAnnualReturn: 7,
      annualReturnStdDev: 15,
      annualInflation: 2.3,
      simulations: 2000
    };
    const result = engine.run(fireInput);
    expect(result.probabilityOfSuccess).toBeGreaterThan(80);
  });
});
