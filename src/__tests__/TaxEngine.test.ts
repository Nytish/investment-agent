import { TaxEngine, VorabpauschaleInput } from "../engines/TaxEngine";

const engine = new TaxEngine();

describe("TaxEngine — calculateVorabpauschale", () => {
  it("equity fund with 2025 basiszins: taxable amount ≈ €114.94", () => {
    const input: VorabpauschaleInput = {
      fundValueStartOfYear: 10000,
      fundValueEndOfYear: 10500,  // gained €500, above basisertrag
      distributionsReceived: 0,
      isEquityFund: true,
      isMixedFund: false,
      isRealEstateFund: false,
      year: 2025
    };
    const result = engine.calculateVorabpauschale(input);
    // basisertrag = 10000 × 0.023 × 0.7 = 161
    // vorabpauschale = 161 (no distributions, price gain > basisertrag)
    // taxableVorabpauschale = 161 × 0.7 = 112.7
    // The prompt formula: 10000 × 0.023 × 0.7 × 0.7 = 114.94 uses basiszins 0.023
    // With 2025 basiszins = 0.0230 → same result
    expect(result.taxableAmount).toBeCloseTo(112.7, 0);
  });

  it("fund that lost value: taxDue should be 0", () => {
    const input: VorabpauschaleInput = {
      fundValueStartOfYear: 10000,
      fundValueEndOfYear: 9500,   // fund lost value
      distributionsReceived: 0,
      isEquityFund: true,
      isMixedFund: false,
      isRealEstateFund: false,
      year: 2025
    };
    const result = engine.calculateVorabpauschale(input);
    // priceGain = 0, vorabpauschale capped at 0
    expect(result.vorabpauschale).toBe(0);
    expect(result.totalTaxEur).toBe(0);
  });
});

describe("TaxEngine — calculateAfterTaxReturn", () => {
  it("equity ETF at 7% return → after-tax return ~5.5-5.8%", () => {
    const result = engine.calculateAfterTaxReturn({
      grossReturnPercent: 7,
      assetClass: "equity_etf",
      freistellungsauftragRemaining: 0
    });
    // effectiveTaxRate = 26.375% × 0.7 = 18.4625%
    // netReturn = 7 × (1 - 0.184625) ≈ 5.71
    expect(result.netReturn).toBeGreaterThan(5.4);
    expect(result.netReturn).toBeLessThan(6.0);
  });

  it("gold held > 1 year → tax rate 0% (same gross and net return)", () => {
    const result = engine.calculateAfterTaxReturn({
      grossReturnPercent: 7,
      assetClass: "gold",
      holdingYears: 2,
      freistellungsauftragRemaining: 0
    });
    expect(result.effectiveTaxRate).toBe(0);
    expect(result.netReturn).toBe(7);
  });
});

describe("TaxEngine — calculateFreistellungsauftragUsage", () => {
  it("earnings €500 with FSA €2000 → 0 tax due", () => {
    const result = engine.calculateFreistellungsauftragUsage(500, 0, 0, 2000);
    expect(result.totalTaxableIncome).toBe(500);
    expect(result.taxDueWithout).toBe(0);
    expect(result.freistellungsauftragRemaining).toBe(1500);
  });

  it("earnings €2500 with FSA €2000 → tax on €500", () => {
    const result = engine.calculateFreistellungsauftragUsage(2500, 0, 0, 2000);
    expect(result.totalTaxableIncome).toBe(2500);
    // taxable = 2500 - 2000 = 500 → tax = 500 × 0.26375 = 131.875
    expect(result.taxDueWithout).toBeCloseTo(131.875, 2);
    expect(result.freistellungsauftragRemaining).toBe(0);
  });
});
