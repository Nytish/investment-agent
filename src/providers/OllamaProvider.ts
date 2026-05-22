// ============================================================
// OllamaProvider — local Ollama HTTP API (OpenAI-compatible)
// Offline fallback: works without internet
// ============================================================

import { FunctionDeclaration } from "@google/generative-ai";
import { LLMProvider, LLMResponse, UnifiedMessage } from "./types";
import crypto from "crypto";

const OLLAMA_BASE = "http://localhost:11434";

interface OllamaMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string;
  tool_calls?: Array<{ function: { name: string; arguments: Record<string, unknown> } }>;
}

interface OllamaTool {
  type: "function";
  function: {
    name: string;
    description: string;
    parameters: Record<string, unknown>;
  };
}

interface OllamaResponse {
  model: string;
  message: {
    role: string;
    content: string;
    tool_calls?: Array<{ function: { name: string; arguments: Record<string, unknown> } }>;
  };
  done: boolean;
}

export class OllamaProvider implements LLMProvider {
  readonly name: string;

  constructor(modelName: string = "qwen2.5:14b") {
    this.name = modelName;
  }

  async isAvailable(): Promise<boolean> {
    try {
      const res = await fetch(`${OLLAMA_BASE}/api/tags`, { signal: AbortSignal.timeout(2000) });
      return res.ok;
    } catch {
      return false;
    }
  }

  async sendTurn(
    history: UnifiedMessage[],
    tools: FunctionDeclaration[],
    systemPrompt: string
  ): Promise<LLMResponse> {
    const messages = this.convertMessages(history, systemPrompt);
    const ollamaTools = this.convertTools(tools);

    const body = {
      model: this.name,
      messages,
      tools: ollamaTools,
      stream: false,
      options: {
        temperature: 0.4,
        num_ctx: 8192
      }
    };

    const res = await fetch(`${OLLAMA_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(60000)   // 60s — local model is slower
    });

    if (!res.ok) {
      throw new Error(`Ollama error: ${res.status} ${res.statusText}`);
    }

    const data = await res.json() as OllamaResponse;
    const msg = data.message;

    if (msg.tool_calls && msg.tool_calls.length > 0) {
      return {
        text: "",
        toolCalls: msg.tool_calls.map(tc => ({
          id: crypto.randomUUID(),
          name: tc.function.name,
          args: tc.function.arguments ?? {}
        })),
        modelUsed: this.name,
        isToolCall: true
      };
    }

    return {
      text: msg.content,
      toolCalls: [],
      modelUsed: this.name,
      isToolCall: false
    };
  }

  private convertMessages(history: UnifiedMessage[], systemPrompt: string): OllamaMessage[] {
    const messages: OllamaMessage[] = [
      { role: "system", content: systemPrompt }
    ];

    for (const msg of history) {
      if (msg.role === "user") {
        messages.push({ role: "user", content: msg.content });
      } else if (msg.role === "assistant") {
        if (msg.toolCalls && msg.toolCalls.length > 0) {
          messages.push({
            role: "assistant",
            content: "",
            tool_calls: msg.toolCalls.map(tc => ({
              function: { name: tc.name, arguments: tc.args }
            }))
          });
        } else {
          messages.push({ role: "assistant", content: msg.content });
        }
      } else if (msg.role === "tool_result") {
        messages.push({ role: "tool", content: msg.content });
      }
    }

    return messages;
  }

  private convertTools(tools: FunctionDeclaration[]): OllamaTool[] {
    return tools.map(tool => ({
      type: "function" as const,
      function: {
        name: tool.name,
        description: tool.description ?? "",
        parameters: (tool.parameters ?? { type: "object", properties: {}, required: [] }) as Record<string, unknown>
      }
    }));
  }
}
