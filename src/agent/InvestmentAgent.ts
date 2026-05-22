// ============================================================
// InvestmentAgent — Gemini tool-calling loop
// Orchestrates conversation + tool execution
// ============================================================

import {
  GoogleGenerativeAI,
  ChatSession,
  FunctionCallingMode,
  Content
} from "@google/generative-ai";
import * as dotenv from "dotenv";
import { SYSTEM_PROMPT } from "./prompts";
import { TOOL_DECLARATIONS, executeTool } from "./tools";
import { HOLDING_TOOL_DECLARATIONS, executeHoldingTool } from "./holdingTools";
import { INSIGHT_TOOL_DECLARATIONS, executeInsightTool } from "./insightTools";
import { NOTIFICATION_TOOL_DECLARATIONS, executeNotificationTool } from "./notificationTools";
import { TAX_TOOL_DECLARATIONS, executeTaxTool } from "./taxTools";
import { saveConversationMessage } from "../services/FirestoreService";
import { NITISH_UID } from "../services/SeedData";

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

dotenv.config();

export interface AgentResponse {
  text: string;
  toolsUsed: string[];
  sessionId: string;
}

export class InvestmentAgent {
  private genAI: GoogleGenerativeAI;
  private chat: ChatSession | null = null;
  private sessionId: string;
  private toolsUsedInTurn: string[] = [];

  constructor() {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      throw new Error("GEMINI_API_KEY not set in .env file");
    }

    this.genAI = new GoogleGenerativeAI(apiKey);
    this.sessionId = `session_${Date.now()}`;
  }

  // Start a new conversation session
  startSession(priorHistory: Content[] = []): void {
    const model = this.genAI.getGenerativeModel({
      model: "gemini-2.5-flash",
      systemInstruction: SYSTEM_PROMPT,
      tools: [{ functionDeclarations: ALL_TOOL_DECLARATIONS }],
      toolConfig: {
        functionCallingConfig: {
          mode: FunctionCallingMode.AUTO
        }
      },
      generationConfig: {
        temperature: 0.4,       // lower = more consistent financial advice
        maxOutputTokens: 2048
      }
    });

    this.chat = model.startChat({
      history: priorHistory
    });

    this.sessionId = `session_${Date.now()}`;
  }

  // Retry helper — handles 503 / 429 with exponential backoff
  private async sendWithRetry(
    fn: () => Promise<unknown>,
    maxRetries = 3
  ): Promise<unknown> {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await fn();
      } catch (err) {
        const msg = (err as Error).message ?? "";
        const isRetryable = msg.includes("503") || msg.includes("429") || msg.includes("overloaded");
        if (!isRetryable || attempt === maxRetries) throw err;
        const delayMs = attempt * 2000; // 2s, 4s, 6s
        console.log(`[agent] Gemini ${msg.includes("503") ? "503" : "429"} — retry ${attempt}/${maxRetries} in ${delayMs / 1000}s`);
        await new Promise(r => setTimeout(r, delayMs));
      }
    }
  }

  // Send a message and get a response (handles tool calling loop)
  async chat_message(userMessage: string): Promise<AgentResponse> {
    if (!this.chat) {
      this.startSession();
    }

    this.toolsUsedInTurn = [];

    // Save user message to Firestore (fire-and-forget)
    saveConversationMessage(NITISH_UID, this.sessionId, {
      role: "user",
      content: userMessage,
      timestamp: new Date().toISOString()
    }).catch(() => { /* non-blocking */ });

    const chat = this.chat!;
    let result = await this.sendWithRetry(() => chat.sendMessage(userMessage)) as Awaited<ReturnType<typeof chat.sendMessage>>;

    // Tool-calling loop — keep running until Gemini gives a text response
    while (true) {
      const response = result.response;
      const functionCalls = response.functionCalls();

      if (!functionCalls || functionCalls.length === 0) {
        // No more tool calls — final text response
        const finalText = response.text();

        // Save agent response to Firestore
        saveConversationMessage(NITISH_UID, this.sessionId, {
          role: "model",
          content: finalText,
          timestamp: new Date().toISOString()
        }).catch(() => { /* non-blocking */ });

        return {
          text: finalText,
          toolsUsed: this.toolsUsedInTurn,
          sessionId: this.sessionId
        };
      }

      // Execute all function calls in parallel
      const toolResponses = await Promise.all(
        functionCalls.map(async (fc) => {
          this.toolsUsedInTurn.push(fc.name);
          const toolResult = await executeAnyTool(fc.name, fc.args as Record<string, unknown>);
          return {
            functionResponse: {
              name: fc.name,
              response: toolResult as Record<string, unknown>
            }
          };
        })
      );

      // Send tool results back to Gemini
      result = await this.sendWithRetry(() => chat.sendMessage(toolResponses)) as Awaited<ReturnType<typeof chat.sendMessage>>;
    }
  }

  getSessionId(): string {
    return this.sessionId;
  }

  resetSession(): void {
    this.chat = null;
    this.sessionId = `session_${Date.now()}`;
  }
}
