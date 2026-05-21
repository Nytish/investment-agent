// ============================================================
// TaxCornerService — German tax calendar + Elster prep guidance
// Specific to Nitish's situation: Steuerklasse III, expat, ETF investor
// ============================================================

export interface TaxDeadline {
  date: string;
  description: string;
  urgency: "critical" | "important" | "info";
  daysUntil: number;
}

export interface ElsterField {
  anlage: string;       // e.g. "KAP", "AUS", "Hauptvordruck"
  fieldNumber: string;  // e.g. "KAP Zeile 7"
  description: string;
  nitishValue: string;  // Pre-filled guidance for Nitish's situation
  notes?: string;
}

export interface TaxYear {
  year: number;
  estimatedVorabpauschale: number;
  freistellungsauftrag: number;
  remainingFSA: number;
  taxableCapitalGains: number;
  taxDue: number;
}

// German tax deadlines relevant to Nitish (2026)
export function getTaxDeadlines(): TaxDeadline[] {
  const now = new Date();
  const year = now.getFullYear();

  const deadlines = [
    {
      date: `${year}-01-01`,
      description: "Vorabpauschale: Scalable Capital zieht automatisch ab. Cash-Puffer prüfen.",
      urgency: "important" as const
    },
    {
      date: `${year}-01-31`,
      description: "Jahressteuerbescheinigung von Scalable Capital verfügbar (meist Feb).",
      urgency: "info" as const
    },
    {
      date: `${year}-02-28`,
      description: "Jahressteuerbescheinigung von DKB/Scalable herunterladen.",
      urgency: "important" as const
    },
    {
      date: `${year}-07-31`,
      description: `Steuererklärung ${year - 1} Abgabefrist (ohne Steuerberater). Mit Berater: 28. Feb ${year + 1}.`,
      urgency: "critical" as const
    },
    {
      date: `${year}-12-31`,
      description: "Freistellungsauftrag für nächstes Jahr anpassen falls nötig.",
      urgency: "info" as const
    }
  ];

  return deadlines.map(d => {
    const deadlineDate = new Date(d.date);
    const daysUntil = Math.ceil((deadlineDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    return { ...d, daysUntil };
  }).sort((a, b) => Math.abs(a.daysUntil) - Math.abs(b.daysUntil));
}

// Elster field guidance for Nitish's situation
export function getElsterFieldGuide(category: "KAP" | "AUS" | "expat" | "all"): ElsterField[] {
  const kapFields: ElsterField[] = [
    {
      anlage: "KAP",
      fieldNumber: "Zeile 7",
      description: "Kapitalerträge inländischer Kapitalanlagen (Zinsen Tagesgeld, ETF-Dividenden)",
      nitishValue: "Aus Jahressteuerbescheinigung DKB Tagesgeld + Scalable Capital übertragen",
      notes: "Beträge bereits mit Abgeltungsteuer versteuert — nur zur Günstigerprüfung relevant"
    },
    {
      anlage: "KAP",
      fieldNumber: "Zeile 14-16",
      description: "Vorabpauschale aus Investmentfonds (VWCE, IS3N, IWDP)",
      nitishValue: "Aus Scalable Jahressteuerbescheinigung — Vorabpauschale nach Teilfreistellung",
      notes: "Scalable zieht automatisch ab. Zeile 15 = Vorabpauschale Aktienfonds (70% steuerpflichtig)"
    },
    {
      anlage: "KAP",
      fieldNumber: "Zeile 19",
      description: "Freistellungsauftrag — genutzter Betrag",
      nitishValue: "Max €2.000 (Steuerklasse III, verheiratet). Aus Steuerbescheinigung übernehmen.",
      notes: "Übersteigt Ertrag €2.000, ist der Rest mit 26,375% zu versteuern"
    },
    {
      anlage: "KAP",
      fieldNumber: "Zeile 41-43",
      description: "Günstigerprüfung beantragen",
      nitishValue: "Nur sinnvoll wenn persönlicher Steuersatz < 25% (Einkommen unter ~20.000 €/Jahr)",
      notes: "Bei Nitish's Gehalt (ca. €48K brutto) nicht relevant — Abgeltungsteuer ist günstiger"
    }
  ];

  const ausFields: ElsterField[] = [
    {
      anlage: "AUS",
      fieldNumber: "Zeile 5-10",
      description: "Ausländische Kapitalerträge (VWCE IE-domiziliert, IS3N)",
      nitishValue: "Irland-domizilierte UCITS ETFs: In Deutschland vollständig abgeltungsteuerpflichtig. Keine Doppelbesteuerung DE-IE.",
      notes: "VWCE (IE00BK5BQT80) und IS3N (IE00BKM4GZ66) sind irische Fonds — werden von Scalable korrekt besteuert"
    },
    {
      anlage: "AUS",
      fieldNumber: "Zeile 12",
      description: "Anrechnung ausländischer Quellensteuer",
      nitishValue: "Bei UCITS ETFs über deutschen Broker: Quellensteuer meist bereits angerechnet (Muster DBA DE-IE). Scalable übernimmt.",
      notes: "Kein manueller Eintrag nötig wenn Scalable als Depotbank"
    }
  ];

  const expatFields: ElsterField[] = [
    {
      anlage: "Hauptvordruck",
      fieldNumber: "Zeile 21-22",
      description: "Unbeschränkte Steuerpflicht in Deutschland (Wohnsitz Bayern)",
      nitishValue: "Ja — vollständig unbeschränkt steuerpflichtig seit Einzug nach Deutschland",
      notes: "Indisches Gehalt aus Vorjahr: DBA DE-IN prüfen (Ansässigkeitsbescheinigung nötig)"
    },
    {
      anlage: "Anlage N",
      fieldNumber: "Zeile 6",
      description: "Arbeitslohn von Luxoft (Deutschland)",
      nitishValue: "Aus Lohnsteuerbescheinigung Luxoft Germany. Steuerklasse III.",
      notes: "Lohnsteuerbescheinigung kommt von HR bis Ende Februar"
    },
    {
      anlage: "Anlage Kind",
      fieldNumber: "Zeile 4-6",
      description: "Kinderfreibetrag für Kind (geb. 31.12.2024)",
      nitishValue: "Kind ab 31.12.2024 — ganzes Jahr 2025 zählt! Kindergeld €255/Monat bereits erhalten.",
      notes: "Finanzamt prüft automatisch ob Kinderfreibetrag oder Kindergeld günstiger"
    },
    {
      anlage: "Anlage Kind",
      fieldNumber: "Zeile 40-43",
      description: "Elterngeld (Elterngeld Plus oder Basiselterngeld)",
      nitishValue: "Elterngeld ist steuerfrei, erhöht aber Steuersatz (Progressionsvorbehalt §32b EStG). In Hauptvordruck Zeile 29.",
      notes: "WICHTIG: Elterngeld in Hauptvordruck Zeile 29 eintragen — wird für Steuersatzberechnung verwendet"
    },
    {
      anlage: "Hinweis",
      fieldNumber: "Indischer PF",
      description: "Indischer Provident Fund (EPF/PPF)",
      nitishValue: "Erst bei Auszahlung steuerpflichtig in Deutschland. Jährliche Erträge prüfen — möglicherweise als ausländische Kapitaleinkünfte zu deklarieren.",
      notes: "DBA DE-IN Artikel 20 prüfen. Bei Auszahlung: Anlage AUS + evtl. Anlage VL"
    }
  ];

  switch (category) {
    case "KAP": return kapFields;
    case "AUS": return ausFields;
    case "expat": return expatFields;
    case "all": return [...kapFields, ...ausFields, ...expatFields];
  }
}

// Quick tax year summary for Nitish (2025/2026 focused)
export function getTaxYearSummary(year: number, portfolioValue: number): TaxYear {
  // Basiszins by year
  const basiszinsMap: Record<number, number> = {
    2024: 0.0262,
    2025: 0.0230,
    2026: 0.0210
  };
  const basiszins = basiszinsMap[year] ?? 0.0210;

  // Vorabpauschale estimate: portfolioValue × basiszins × 0.7 × 0.7 (equity Teilfreistellung)
  const basisertrag = portfolioValue * basiszins * 0.7;
  const taxableAfterTeilfreistellung = basisertrag * 0.7;   // 30% Teilfreistellung for equity ETFs
  const estimatedVorabpauschale = Math.max(0, taxableAfterTeilfreistellung);

  const freistellungsauftrag = 2000;
  const remainingFSA = Math.max(0, freistellungsauftrag - estimatedVorabpauschale);
  const taxableCapitalGains = Math.max(0, estimatedVorabpauschale - freistellungsauftrag);
  const taxDue = taxableCapitalGains * 0.26375;   // 25% + 5.5% Soli

  return {
    year,
    estimatedVorabpauschale: Math.round(estimatedVorabpauschale * 100) / 100,
    freistellungsauftrag,
    remainingFSA: Math.round(remainingFSA * 100) / 100,
    taxableCapitalGains: Math.round(taxableCapitalGains * 100) / 100,
    taxDue: Math.round(taxDue * 100) / 100
  };
}
