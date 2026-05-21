// ============================================================
// holdingTools — Gemini tool declarations + executor
// for portfolio holdings management
// ============================================================

import { FunctionDeclaration, SchemaType } from "@google/generative-ai";
import {
  getHoldings,
  addHolding,
  updateHolding,
  deleteHolding,
  calculatePortfolioSummary
} from "../services/HoldingsService";
import { NITISH_UID } from "../services/SeedData";
import { AssetClass } from "../models/Portfolio";

// ── Tool declarations (sent to Gemini) ───────────────────────

export const HOLDING_TOOL_DECLARATIONS: FunctionDeclaration[] = [
  {
    name: "getPortfolioHoldings",
    description:
      "Get all current portfolio holdings with values, asset classes, and allocation percentages",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {},
      required: []
    }
  },
  {
    name: "addPortfolioHolding",
    description: "Add a new investment holding to the portfolio tracker",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {
        name: {
          type: SchemaType.STRING,
          description: "Name of the holding, e.g. 'Vanguard FTSE All-World UCITS ETF'"
        },
        assetClass: {
          type: SchemaType.STRING,
          description:
            "Asset class: world_etf | em_etf | bonds | gold | reit | crypto | cash | individual_stock"
        },
        isin: {
          type: SchemaType.STRING,
          description: "ISIN code, e.g. IE00BK5BQT80 (optional)"
        },
        broker: {
          type: SchemaType.STRING,
          description: "Broker or platform where the holding is held"
        },
        currentValue: {
          type: SchemaType.NUMBER,
          description: "Current market value in EUR"
        },
        purchaseDate: {
          type: SchemaType.STRING,
          description: "Date of purchase in ISO format YYYY-MM-DD (optional)"
        },
        notes: {
          type: SchemaType.STRING,
          description: "Optional notes about the holding"
        }
      },
      required: ["name", "assetClass", "broker", "currentValue"]
    }
  },
  {
    name: "updateHoldingValue",
    description: "Update the current market value of an existing holding",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {
        holdingId: {
          type: SchemaType.STRING,
          description: "Unique identifier of the holding to update"
        },
        newValueEur: {
          type: SchemaType.NUMBER,
          description: "New current market value in EUR"
        }
      },
      required: ["holdingId", "newValueEur"]
    }
  },
  {
    name: "deleteHolding",
    description: "Remove a holding from the portfolio",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {
        holdingId: {
          type: SchemaType.STRING,
          description: "Unique identifier of the holding to remove"
        }
      },
      required: ["holdingId"]
    }
  }
];

// ── Tool executor ─────────────────────────────────────────────

export async function executeHoldingTool(
  name: string,
  args: Record<string, unknown>
): Promise<unknown> {
  switch (name) {

    case "getPortfolioHoldings": {
      const holdings = await getHoldings(NITISH_UID);
      const summary = calculatePortfolioSummary(holdings);
      return {
        holdings,
        summary
      };
    }

    case "addPortfolioHolding": {
      const holding = await addHolding(NITISH_UID, {
        name: args.name as string,
        assetClass: args.assetClass as AssetClass,
        isin: args.isin as string | undefined,
        broker: args.broker as string,
        currentValue: args.currentValue as number,
        purchaseDate: args.purchaseDate as string | undefined,
        notes: args.notes as string | undefined
      });
      return {
        success: true,
        holding,
        message: `Holding "${holding.name}" added with id ${holding.id}.`
      };
    }

    case "updateHoldingValue": {
      const updated = await updateHolding(
        NITISH_UID,
        args.holdingId as string,
        { currentValue: args.newValueEur as number }
      );
      if (!updated) {
        return {
          success: false,
          message: `Holding with id "${args.holdingId}" not found.`
        };
      }
      return {
        success: true,
        holding: updated,
        message: `Holding "${updated.name}" updated to €${updated.currentValue}.`
      };
    }

    case "deleteHolding": {
      const removed = await deleteHolding(NITISH_UID, args.holdingId as string);
      return {
        success: removed,
        message: removed
          ? `Holding "${args.holdingId}" removed from portfolio.`
          : `Holding with id "${args.holdingId}" not found.`
      };
    }

    default:
      return { error: `Unknown holding tool: ${name}` };
  }
}
