// ============================================================
// InvestmentAgent — provider-agnostic tool-calling loop
// Routes: gemini-2.5-flash → gemini-1.5-flash → qwen2.5:14b
// ============================================================

import * as dotenv from "dotenv";
import { SYSTEM_PROMPT } from "./prompts";
import { TOOL_DECLARATIONS, executeTool } from "./tools";
import { HOLDING_TOOL_DECLARATIONS, executeHoldingTool } from "./holdingTools";
import { INSIGHT_TOOL_DECLARATIONS, executeInsightTool } from "./insightTools";
import { NOTIFICATION_TOOL_DECLARATIONS, executeNotificationTool } from "./notificationTools";
import { TAX_TOOL_DECLARATIONS, executeTaxTool } from "./taxTools";
import { saveConversationMessage } from "../services/FirestoreService";
import { NITISH_UID } from "../services/SeedData";
import { routeToModel } from "../providers/ModelRouter";
import { UnifiedMessage } from "../providers/types";

dotenv.config();

const ALL_TOOL_DECLARATIONS = [
  ...TOOL_DECLARATIONS,
  ...HOLDING_TOOL_DECLARATIONS,
  ...INSIGHT_TOOL_DECLARATIONS,
  ...NOTIFICATION_TOOL_DECLARATIONS,
  ...TAX_TOOL_DECLARATIONS
];

async function executeAnyTool(name: string, args: Record<string, unknown>): Promise<unknown> {
  const holdingNames = HOLDING_TOOL_DECLARATIONS.map(t => t.name);
  const insightNames = INSIGHT_TOOL_DECLARATIONS.map(t => t.name);
  const notifNames   = NOTIFICATION_TOOL_DECLARATIONS.map(t => t.name);
  const taxNames     = TAX_TOOL_DECLARATIONS.map(t => t.name);
  if (holdingNames.includes(name)) return executeHoldingTool(name, args);
  if (insightNames.includes(name)) return executeInsightTool(name, args);
  if (notifNames.includes(name))   return executeNotificationTool(name, args);
  if (taxNames.includes(name))     return executeTaxTool(name, args);
  return executeTool(name, args);
}

export interface AgentResponse {
  text: string;
  toolsUsed: string[];
  sessionId: string;
  modelUsed: string;
}

export class InvestmentAgent {
  private history: UnifiedMessage[] = [];
  private sessionId: string;
  private toolsUsedInTurn: string[] = [];

  constructor() {
    this.sessionId = `session_${Date.now()}`;
  }

  // Keep startSession() for backward compatibility with index.ts (CLI)
  startSession(): void {
    this.history = [];
    this.sessionId = `session_${Date.now()}`;
  }

  async chat_message(userMessage: string): Promise<AgentResponse> {
    this.toolsUsedInTurn = [];

    // Add user message to history
    this.history.push({ role: "user", content: userMessage });

    // Save to Firestore (fire-and-forget)
    saveConversationMessage(NITISH_UID, this.sessionId, {
      role: "user",
      content: userMessage,
      timestamp: new Date().toISOString()
    }).catch(() => { /* non-blocking */ });

    // Tool-calling loop
    while (true) {
      const response = await routeToModel(this.history, ALL_TOOL_DECLARATIONS, SYSTEM_PROMPT);

      if (!response.isToolCall) {
        // Final text answer
        this.history.push({ role: "assistant", content: response.text });

        saveConversationMessage(NITISH_UID, this.sessionId, {
          role: "model",
          content: response.text,
          timestamp: new Date().toISOString()
        }).catch(() => { /* non-blocking */ });

        return {
          text: response.text,
          toolsUsed: this.toolsUsedInTurn,
          sessionId: this.sessionId,
          modelUsed: response.modelUsed
        };
      }

      // Model requested tool calls — add to history
      this.history.push({
        role: "assistant",
        content: "",
        toolCalls: response.toolCalls
      });

      // Execute all tools in parallel
      const toolResults = await Promise.all(
        response.toolCalls.map(async (tc) => {
          this.toolsUsedInTurn.push(tc.name);
          const result = await executeAnyTool(tc.name, tc.args);
          return {
            toolCallId: tc.id,
            toolName: tc.name,
            content: JSON.stringify(result)
          };
        })
      );

      // Add tool results to history (individual messages — providers group as needed)
      for (const tr of toolResults) {
        this.history.push({
          role: "tool_result",
          content: tr.content,
          toolCallId: tr.toolCallId,
          toolName: tr.toolName
        });
      }
    }
  }

  getSessionId(): string {
    return this.sessionId;
  }

  resetSession(): void {
    this.history = [];
    this.sessionId = `session_${Date.now()}`;
  }
}
