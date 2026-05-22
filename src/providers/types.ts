// ============================================================
// Provider Types — unified LLM interface
// All providers (Gemini, Ollama) implement LLMProvider
// ============================================================

import { FunctionDeclaration } from "@google/generative-ai";

// Unified conversation history — provider-agnostic
export interface UnifiedMessage {
  role: "user" | "assistant" | "tool_result";
  content: string;
  // Present on assistant messages that triggered tool calls
  toolCalls?: UnifiedToolCall[];
  // Present on tool_result messages
  toolCallId?: string;
  toolName?: string;
}

export interface UnifiedToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
}

export interface LLMResponse {
  text: string;                        // empty string if toolCalls present
  toolCalls: UnifiedToolCall[];        // empty array if text present
  modelUsed: string;                   // e.g. "gemini-1.5-flash" or "qwen2.5:14b"
  isToolCall: boolean;
}

// Every provider must implement this interface
export interface LLMProvider {
  readonly name: string;
  isAvailable(): Promise<boolean>;
  sendTurn(
    history: UnifiedMessage[],
    tools: FunctionDeclaration[],
    systemPrompt: string
  ): Promise<LLMResponse>;
}
