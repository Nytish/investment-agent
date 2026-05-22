// ============================================================
// ModelRouter — tries providers in priority order
// gemini-2.5-flash → gemini-1.5-flash → qwen2.5:14b (local)
// ============================================================

import { FunctionDeclaration } from "@google/generative-ai";
import { LLMProvider, LLMResponse, UnifiedMessage } from "./types";
import { GeminiProvider } from "./GeminiProvider";
import { OllamaProvider } from "./OllamaProvider";

const PROVIDERS: LLMProvider[] = [
  new GeminiProvider("gemini-2.5-flash"),
  new GeminiProvider("gemini-1.5-flash"),
  new OllamaProvider("qwen2.5:14b")
];

export let lastModelUsed = "unknown";

function isTransientError(err: Error): boolean {
  const msg = err.message ?? "";
  return (
    msg.includes("503") ||
    msg.includes("429") ||
    msg.includes("overloaded") ||
    msg.includes("ECONNREFUSED") ||
    msg.includes("fetch failed") ||
    msg.includes("network") ||
    msg.includes("timeout")
  );
}

export async function routeToModel(
  history: UnifiedMessage[],
  tools: FunctionDeclaration[],
  systemPrompt: string
): Promise<LLMResponse> {
  const failures: string[] = [];

  for (const provider of PROVIDERS) {
    const available = await provider.isAvailable();
    if (!available) {
      failures.push(`${provider.name}: not available`);
      continue;
    }

    try {
      console.log(`[router] Trying ${provider.name}...`);
      const response = await provider.sendTurn(history, tools, systemPrompt);
      lastModelUsed = provider.name;
      console.log(`[router] ✓ Answered by ${provider.name}`);
      return response;
    } catch (err) {
      const error = err as Error;
      if (isTransientError(error)) {
        console.log(`[router] ${provider.name} failed (${error.message.slice(0, 60)}) — trying next`);
        failures.push(`${provider.name}: ${error.message.slice(0, 60)}`);
        continue;
      }
      throw error;   // non-transient error — rethrow immediately
    }
  }

  throw new Error(
    `All LLM providers unavailable.\n${failures.map(f => `  • ${f}`).join("\n")}\n` +
    `Tip: Run 'ollama serve' for offline mode.`
  );
}
