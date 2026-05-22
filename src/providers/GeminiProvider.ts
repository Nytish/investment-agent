// ============================================================
// GeminiProvider — wraps @google/generative-ai
// Stateless: reconstructs ChatSession from full history each call
// ============================================================

import {
  GoogleGenerativeAI,
  FunctionDeclaration,
  FunctionCallingMode,
  Content,
  Part
} from "@google/generative-ai";
import * as dotenv from "dotenv";
import { LLMProvider, LLMResponse, UnifiedMessage, UnifiedToolCall } from "./types";
import crypto from "crypto";

dotenv.config();

export class GeminiProvider implements LLMProvider {
  readonly name: string;
  private genAI: GoogleGenerativeAI;

  constructor(modelName: string) {
    this.name = modelName;
    const apiKey = process.env.GEMINI_API_KEY ?? "";
    this.genAI = new GoogleGenerativeAI(apiKey);
  }

  async isAvailable(): Promise<boolean> {
    return !!process.env.GEMINI_API_KEY;
  }

  async sendTurn(
    history: UnifiedMessage[],
    tools: FunctionDeclaration[],
    systemPrompt: string
  ): Promise<LLMResponse> {
    const allContents = this.convertToGeminiContents(history);

    // Split: prior history (for startChat) + last message (for sendMessage)
    const priorContents = allContents.slice(0, -1);
    const lastContent = allContents[allContents.length - 1];
    const toSend: Part[] = lastContent.parts as Part[];

    const model = this.genAI.getGenerativeModel({
      model: this.name,
      systemInstruction: systemPrompt,
      tools: [{ functionDeclarations: tools }],
      toolConfig: { functionCallingConfig: { mode: FunctionCallingMode.AUTO } },
      generationConfig: { temperature: 0.4, maxOutputTokens: 2048 }
    });

    const chat = model.startChat({ history: priorContents });
    const result = await chat.sendMessage(toSend);
    const response = result.response;

    const functionCalls = response.functionCalls();
    if (functionCalls && functionCalls.length > 0) {
      return {
        text: "",
        toolCalls: functionCalls.map(fc => ({
          id: crypto.randomUUID(),
          name: fc.name,
          args: fc.args as Record<string, unknown>
        })),
        modelUsed: this.name,
        isToolCall: true
      };
    }

    return {
      text: response.text(),
      toolCalls: [],
      modelUsed: this.name,
      isToolCall: false
    };
  }

  private convertToGeminiContents(history: UnifiedMessage[]): Content[] {
    const contents: Content[] = [];
    let i = 0;

    while (i < history.length) {
      const msg = history[i];

      if (msg.role === "user") {
        contents.push({ role: "user", parts: [{ text: msg.content }] });
        i++;
      } else if (msg.role === "assistant") {
        if (msg.toolCalls && msg.toolCalls.length > 0) {
          contents.push({
            role: "model",
            parts: msg.toolCalls.map(tc => ({
              functionCall: { name: tc.name, args: tc.args }
            }))
          });
        } else {
          contents.push({ role: "model", parts: [{ text: msg.content }] });
        }
        i++;
      } else if (msg.role === "tool_result") {
        // Group consecutive tool_result messages into ONE Gemini user message
        const functionResponseParts: Part[] = [];
        while (i < history.length && history[i].role === "tool_result") {
          const tr = history[i];
          let responseObj: Record<string, unknown>;
          try {
            responseObj = JSON.parse(tr.content) as Record<string, unknown>;
          } catch {
            responseObj = { result: tr.content };
          }
          functionResponseParts.push({
            functionResponse: {
              name: tr.toolName!,
              response: responseObj
            }
          });
          i++;
        }
        contents.push({ role: "user", parts: functionResponseParts });
      } else {
        i++;
      }
    }

    return contents;
  }
}
