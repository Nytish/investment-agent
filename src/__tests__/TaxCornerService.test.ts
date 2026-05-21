import {
  getTaxDeadlines,
  getElsterFieldGuide,
  getTaxYearSummary
} from "../services/TaxCornerService";

describe("TaxCornerService — getTaxDeadlines", () => {
  it("returns an array with at least 3 deadlines", () => {
    const deadlines = getTaxDeadlines();
    expect(Array.isArray(deadlines)).toBe(true);
    expect(deadlines.length).toBeGreaterThanOrEqual(3);
  });

  it("all deadlines have a daysUntil field of type number", () => {
    const deadlines = getTaxDeadlines();
    deadlines.forEach(d => {
      expect(typeof d.daysUntil).toBe("number");
    });
  });

  it("at least one deadline has urgency 'critical'", () => {
    const deadlines = getTaxDeadlines();
    const criticals = deadlines.filter(d => d.urgency === "critical");
    expect(criticals.length).toBeGreaterThanOrEqual(1);
  });
});

describe("TaxCornerService — getElsterFieldGuide", () => {
  it("getElsterFieldGuide('KAP') returns array with length > 0, each field has required properties", () => {
    const fields = getElsterFieldGuide("KAP");
    expect(Array.isArray(fields)).toBe(true);
    expect(fields.length).toBeGreaterThan(0);
    fields.forEach(f => {
      expect(f).toHaveProperty("anlage");
      expect(f).toHaveProperty("fieldNumber");
      expect(f).toHaveProperty("description");
      expect(f).toHaveProperty("nitishValue");
    });
  });

  it("getElsterFieldGuide('expat') includes a field mentioning 'Elterngeld' or 'Kind'", () => {
    const fields = getElsterFieldGuide("expat");
    const relevant = fields.filter(
      f =>
        f.description.includes("Elterngeld") ||
        f.description.includes("Kind") ||
        f.nitishValue.includes("Elterngeld") ||
        f.nitishValue.includes("Kind")
    );
    expect(relevant.length).toBeGreaterThan(0);
  });
});

describe("TaxCornerService — getTaxYearSummary", () => {
  it("getTaxYearSummary(2026, 50000) returns estimatedVorabpauschale > 0", () => {
    const summary = getTaxYearSummary(2026, 50000);
    // basisertrag = 50000 × 0.021 × 0.7 = 735
    // estimatedVorabpauschale = 735 × 0.7 = 514.5
    expect(summary.estimatedVorabpauschale).toBeGreaterThan(0);
  });

  it("getTaxYearSummary(2026, 50000) freistellungsauftrag is 2000", () => {
    const summary = getTaxYearSummary(2026, 50000);
    expect(summary.freistellungsauftrag).toBe(2000);
  });

  it("getTaxYearSummary(2026, 1000) with tiny portfolio — taxDue is 0 (under FSA)", () => {
    const summary = getTaxYearSummary(2026, 1000);
    // basisertrag = 1000 × 0.021 × 0.7 = 14.7
    // estimatedVorabpauschale = 14.7 × 0.7 = 10.29
    // taxableCapitalGains = max(0, 10.29 - 2000) = 0 → taxDue = 0
    expect(summary.taxDue).toBe(0);
  });
});
