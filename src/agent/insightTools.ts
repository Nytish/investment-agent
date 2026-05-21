// ============================================================
// insightTools — Gemini tool declarations for weekly insights
// Exposes generateWeeklyInsight and getLatestInsight as agent tools
// ============================================================

import { FunctionDeclaration, SchemaType } from "@google/generative-ai";
import { NITISH_PROFILE, NITISH_UID } from "../services/SeedData";
import {
  generateWeeklyInsight,
  saveInsight,
  getLatestInsight,
} from "../services/InsightService";

// ── Tool declarations (sent to Gemini) ───────────────────────

export const INSIGHT_TOOL_DECLARATIONS: FunctionDeclaration[] = [
  {
    name: "generateWeeklyInsight",
    description:
      "Generate a personalized AI-powered weekly investment insight for Nitish based on his portfolio and financial goals. Includes market context, portfolio relevance, and one concrete action item.",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {},
      required: [],
    },
  },
  {
    name: "getLatestInsight",
    description:
      "Retrieve the most recently generated weekly investment insight",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {},
      required: [],
    },
  },
];

// ── Tool executors ────────────────────────────────────────────

export async function executeInsightTool(
  name: string,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _args: Record<string, unknown>
): Promise<unknown> {
  switch (name) {
    case "generateWeeklyInsight": {
      const insight = await generateWeeklyInsight(NITISH_PROFILE);
      await saveInsight(NITISH_UID, insight);
      return insight;
    }

    case "getLatestInsight": {
      const insight = await getLatestInsight(NITISH_UID);
      if (!insight) {
        return { message: "No insights yet. Ask me to generate one." };
      }
      return insight;
    }

    default:
      return { error: `Unknown insight tool: ${name}` };
  }
}
