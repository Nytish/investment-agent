// ============================================================
// Tax Tools — Gemini function declarations + executors
// German tax: Vorabpauschale, Freistellungsauftrag, Elster guide
// ============================================================

import { FunctionDeclaration, SchemaType } from "@google/generative-ai";
import { getTaxDeadlines, getElsterFieldGuide, getTaxYearSummary } from "../services/TaxCornerService";

export const TAX_TOOL_DECLARATIONS: FunctionDeclaration[] = [
  {
    name: "getTaxDeadlines",
    description: "Get upcoming German tax deadlines for Nitish. Includes Vorabpauschale date, Steuererklärung deadline, Jahressteuerbescheinigung availability. Sorted by proximity.",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {},
      required: []
    }
  },
  {
    name: "getElsterGuide",
    description: "Get step-by-step Elster tax return guidance for Nitish's situation (expat, Steuerklasse III, ETF investor, Elterngeld). Shows which Anlage to fill and exact field values.",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {
        category: {
          type: SchemaType.STRING,
          description: "Which tax form area: 'KAP' (capital gains), 'AUS' (foreign income), 'expat' (expat-specific), 'all' (everything)"
        }
      },
      required: ["category"]
    }
  },
  {
    name: "getTaxYearSummary",
    description: "Get a complete tax year summary: estimated Vorabpauschale, Freistellungsauftrag usage, tax due. Pre-calculates everything for Nitish's ETF portfolio.",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {
        year: {
          type: SchemaType.NUMBER,
          description: "Tax year (2024, 2025, or 2026)"
        },
        portfolioValue: {
          type: SchemaType.NUMBER,
          description: "Total ETF portfolio value in EUR at start of year. Defaults to current holdings value."
        }
      },
      required: ["year"]
    }
  }
];

export async function executeTaxTool(name: string, args: Record<string, unknown>): Promise<unknown> {
  switch (name) {
    case "getTaxDeadlines": {
      const deadlines = getTaxDeadlines();
      const upcoming = deadlines.filter(d => d.daysUntil >= -30);  // Show past 30 days too
      const overdue = deadlines.filter(d => d.daysUntil < -30);

      return {
        currentYear: new Date().getFullYear(),
        upcomingDeadlines: upcoming,
        overdueDeadlines: overdue,
        nextCritical: upcoming.find(d => d.urgency === "critical"),
        tip: "Freistellungsauftrag bis 31.12. für nächstes Jahr aktualisieren falls nötig."
      };
    }

    case "getElsterGuide": {
      const category = (args.category as string) ?? "all";
      const validCategories = ["KAP", "AUS", "expat", "all"] as const;
      type ValidCategory = typeof validCategories[number];
      const cat = validCategories.includes(category as ValidCategory)
        ? (category as ValidCategory)
        : "all";

      const fields = getElsterFieldGuide(cat);

      return {
        category: cat,
        fieldCount: fields.length,
        fields,
        generalTips: [
          "ELSTER-App oder elster.de nutzen — kostenlos und direkt ans Finanzamt",
          "Jahressteuerbescheinigung von Scalable Capital abwarten (meist Februar)",
          "Elterngeld in Hauptvordruck Zeile 29 (Progressionsvorbehalt) — nicht vergessen!",
          "Günstigerprüfung bei Ihrem Einkommensniveau (€48K) i.d.R. nicht relevant",
          "DBA DE-IN für indischen Provident Fund: Steuerberater empfohlen beim ersten Mal"
        ]
      };
    }

    case "getTaxYearSummary": {
      const year = (args.year as number) ?? new Date().getFullYear();
      const portfolioValue = (args.portfolioValue as number) ?? 46791;  // Default: liquid assets

      const summary = getTaxYearSummary(year, portfolioValue);

      return {
        ...summary,
        interpretation: summary.taxDue === 0
          ? `Keine Kapitalertragsteuer fällig — Freistellungsauftrag (€${summary.freistellungsauftrag}) nicht ausgeschöpft. Noch €${summary.remainingFSA} verfügbar.`
          : `Ca. €${summary.taxDue} Kapitalertragsteuer + Soli fällig. Scalable zieht automatisch ab.`,
        nextActions: [
          summary.remainingFSA > 0
            ? `Freistellungsauftrag noch €${summary.remainingFSA} ungenutzt — Tagesgeld-Zinsen prüfen`
            : "Freistellungsauftrag voll ausgeschöpft",
          "Jahressteuerbescheinigung von Scalable Capital herunterladen",
          "Anlage KAP in ELSTER ausfüllen"
        ]
      };
    }

    default:
      return { error: `Unknown tax tool: ${name}` };
  }
}
