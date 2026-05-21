// ============================================================
// TaxEngine — German investment tax calculations
// Vorabpauschale, Freistellungsauftrag, Abgeltungsteuer
// ============================================================

// Bundesbank Basiszins history (used for Vorabpauschale)
// Updated annually on 1 January
const BASISZINS: Record<number, number> = {
  2024: 0.0262, // 2.62%
  2025: 0.0230, // 2.30% (estimated)
  2026: 0.0210  // 2.10% (estimated — update with actual Bundesbank value)
};

export interface VorabpauschaleInput {
  fundValueStartOfYear: number;   // EUR — NAV on 1 January
  fundValueEndOfYear: number;     // EUR — NAV on 31 December
  distributionsReceived: number;  // EUR — dividends paid out during year
  isEquityFund: boolean;          // true for MSCI World ETFs
  isMixedFund: boolean;           // true for mixed asset ETFs
  isRealEstateFund: boolean;      // true for REIT ETFs
  year: number;
}

export interface VorabpauschaleResult {
  year: number;
  basiszins: number;              // %
  basisertrag: number;            // EUR = fundValue × basiszins × 0.7
  vorabpauschale: number;         // EUR = basisertrag - distributions (min 0, max price gain)
  taxableVorabpauschale: number;  // EUR after Teilfreistellung
  teilfreistellung: number;       // 0.3 for equity, 0.15 for mixed, 0 for other
  taxableAmount: number;          // EUR after Freistellungsauftrag
  abgeltungsteuer: number;        // EUR (25%)
  solidaritaetszuschlag: number;  // EUR (5.5% on Abgeltungsteuer)
  totalTaxEur: number;            // EUR
  formula: string;
  notes: string[];
}

export interface AfterTaxReturnInput {
  grossReturnPercent: number;     // e.g. 7.0
  assetClass: "equity_etf" | "bond_etf" | "reit_etf" | "gold" | "tagesgeld" | "individual_stock";
  holdingYears?: number;          // for gold/crypto tax-free rule
  freistellungsauftragRemaining: number; // EUR remaining exempt
}

export interface AfterTaxReturnResult {
  assetClass: string;
  grossReturn: number;
  effectiveTaxRate: number;       // %
  netReturn: number;              // %
  taxNotes: string[];
}

export class TaxEngine {

  // --- VORABPAUSCHALE CALCULATOR ---
  calculateVorabpauschale(input: VorabpauschaleInput): VorabpauschaleResult {
    const {
      fundValueStartOfYear,
      fundValueEndOfYear,
      distributionsReceived,
      isEquityFund,
      isMixedFund,
      isRealEstateFund,
      year
    } = input;

    const basiszins = BASISZINS[year] ?? BASISZINS[2026];

    // Basisertrag = Fondswert (1.1.) × Basiszins × 0.7
    const basisertrag = fundValueStartOfYear * basiszins * 0.7;

    // Price gain during year
    const priceGain = Math.max(0, fundValueEndOfYear - fundValueStartOfYear);

    // Vorabpauschale = Basisertrag - Ausschüttungen, but max = price gain, min = 0
    const rawVorabpauschale = Math.max(0, basisertrag - distributionsReceived);
    const vorabpauschale = Math.min(rawVorabpauschale, priceGain);

    // Teilfreistellung (partial exemption)
    let teilfreistellung = 0;
    if (isEquityFund) teilfreistellung = 0.3;         // 30% exempt for equity ETFs
    else if (isMixedFund) teilfreistellung = 0.15;    // 15% for mixed
    else if (isRealEstateFund) teilfreistellung = 0.6; // 60% for real estate funds

    // Taxable after Teilfreistellung
    const taxableVorabpauschale = vorabpauschale * (1 - teilfreistellung);

    // Apply Abgeltungsteuer (25%) + Soli (5.5% thereof)
    const abgeltungsteuer = taxableVorabpauschale * 0.25;
    const solidaritaetszuschlag = abgeltungsteuer * 0.055;
    const totalTaxEur = abgeltungsteuer + solidaritaetszuschlag;

    const formula = `
VORABPAUSCHALE FORMULA (${year}):
─────────────────────────────────────────────────────
1. Basiszins (${year}):        ${(basiszins * 100).toFixed(2)}%
2. Basisertrag:              €${fundValueStartOfYear.toLocaleString("de-DE")} × ${(basiszins * 100).toFixed(2)}% × 0.7
                           = €${basisertrag.toFixed(2)}
3. Ausschüttungen abziehen:  €${basisertrag.toFixed(2)} - €${distributionsReceived.toFixed(2)}
4. Vorabpauschale:           €${vorabpauschale.toFixed(2)} (capped at price gain €${priceGain.toFixed(2)})
5. Teilfreistellung (${(teilfreistellung * 100).toFixed(0)}%):  €${vorabpauschale.toFixed(2)} × ${(1 - teilfreistellung).toFixed(2)} = €${taxableVorabpauschale.toFixed(2)}
6. Abgeltungsteuer (25%):    €${abgeltungsteuer.toFixed(2)}
7. Solidaritätszuschlag:     €${solidaritaetszuschlag.toFixed(2)}
8. TOTAL TAX DUE:            €${totalTaxEur.toFixed(2)}
─────────────────────────────────────────────────────`;

    const notes: string[] = [];
    if (vorabpauschale === 0) {
      notes.push("Vorabpauschale is 0 — fund did not gain more than Basisertrag. No tax due.");
    }
    notes.push(`Broker (Scalable Capital) deducts tax automatically on 2 January each year.`);
    notes.push(`Ensure €${totalTaxEur.toFixed(2)} cash available in account on 1 January ${year + 1}.`);
    notes.push(`Freistellungsauftrag (€2,000) offsets this tax if not yet fully used.`);

    return {
      year,
      basiszins: basiszins * 100,
      basisertrag,
      vorabpauschale,
      taxableVorabpauschale,
      teilfreistellung,
      taxableAmount: taxableVorabpauschale,
      abgeltungsteuer,
      solidaritaetszuschlag,
      totalTaxEur,
      formula,
      notes
    };
  }

  // --- AFTER-TAX RETURN CALCULATOR ---
  calculateAfterTaxReturn(input: AfterTaxReturnInput): AfterTaxReturnResult {
    const { grossReturnPercent, assetClass, holdingYears, freistellungsauftragRemaining } = input;

    const effectiveTaxRate_abgeltung = 0.25 * 1.055; // 25% + 5.5% Soli = 26.375%
    let effectiveTaxRate = 0;
    const taxNotes: string[] = [];

    switch (assetClass) {
      case "equity_etf":
        // Accumulating ETF: Vorabpauschale annual + exit tax on gains
        // Teilfreistellung reduces effective rate
        effectiveTaxRate = effectiveTaxRate_abgeltung * 0.7; // 70% taxable after 30% Teilfreistellung
        taxNotes.push("30% Teilfreistellung applies → effective tax rate ~18.5% on gains");
        taxNotes.push("Vorabpauschale applies annually (prepayment of future gains)");
        taxNotes.push("Freistellungsauftrag (€2,000) offsets first €2,000 of gains per year");
        break;

      case "gold":
        if (holdingYears && holdingYears >= 1) {
          effectiveTaxRate = 0;
          taxNotes.push("✅ Gold held > 1 year: TAX FREE under §23 EStG (Spekulationsfrist)");
          taxNotes.push("EUWAX Gold II qualifies — physically backed ETP");
          taxNotes.push(`Gross return = Net return = ${grossReturnPercent}%`);
        } else {
          effectiveTaxRate = effectiveTaxRate_abgeltung;
          taxNotes.push("⚠️ Gold held < 1 year: full 26.375% Abgeltungsteuer applies");
          taxNotes.push("Hold for 1+ year to get tax-free treatment");
        }
        break;

      case "tagesgeld":
        effectiveTaxRate = effectiveTaxRate_abgeltung;
        taxNotes.push("Interest income: full 26.375% Abgeltungsteuer");
        taxNotes.push("Freistellungsauftrag covers first €2,000");
        if (freistellungsauftragRemaining > 0) {
          taxNotes.push(`€${freistellungsauftragRemaining.toLocaleString("de-DE")} Freistellungsauftrag remaining — first €${freistellungsauftragRemaining.toLocaleString("de-DE")} of interest is tax-free`);
        }
        break;

      case "bond_etf":
        effectiveTaxRate = effectiveTaxRate_abgeltung; // bonds: no Teilfreistellung
        taxNotes.push("Bond ETFs: no Teilfreistellung — full 26.375% on gains");
        break;

      case "reit_etf":
        effectiveTaxRate = effectiveTaxRate_abgeltung * 0.4; // 60% Teilfreistellung
        taxNotes.push("Real estate ETF: 60% Teilfreistellung → effective tax ~10.5%");
        break;

      case "individual_stock":
        effectiveTaxRate = effectiveTaxRate_abgeltung;
        taxNotes.push("Individual stocks: 26.375% Abgeltungsteuer on dividends + capital gains");
        break;
    }

    const netReturn = grossReturnPercent * (1 - effectiveTaxRate);

    return {
      assetClass,
      grossReturn: grossReturnPercent,
      effectiveTaxRate: Math.round(effectiveTaxRate * 10000) / 100, // percentage
      netReturn: Math.round(netReturn * 100) / 100,
      taxNotes
    };
  }

  // --- FREISTELLUNGSAUFTRAG TRACKER ---
  calculateFreistellungsauftragUsage(
    tagesgeldInterestEur: number,
    etfGainsEur: number,        // realised gains only
    dividendsEur: number,
    freistellungsauftragLimit: number = 2000
  ): {
    totalTaxableIncome: number;
    freistellungsauftragUsed: number;
    freistellungsauftragRemaining: number;
    taxDueWithout: number;
    taxSaved: number;
    utilizationPercent: number;
  } {
    const total = tagesgeldInterestEur + etfGainsEur + dividendsEur;
    const used = Math.min(total, freistellungsauftragLimit);
    const remaining = Math.max(0, freistellungsauftragLimit - total);
    const taxableAfterExemption = Math.max(0, total - freistellungsauftragLimit);
    const taxDue = taxableAfterExemption * 0.26375;
    const taxSaved = used * 0.26375;

    return {
      totalTaxableIncome: total,
      freistellungsauftragUsed: used,
      freistellungsauftragRemaining: remaining,
      taxDueWithout: taxableAfterExemption * 0.26375,
      taxSaved: Math.round(taxSaved * 100) / 100,
      utilizationPercent: Math.round((used / freistellungsauftragLimit) * 100)
    };
  }
}
