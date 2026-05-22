// ============================================================
// Investment Agent — Web Server (localhost:3000)
// Express + chat API. Open browser to chat with your agent.
// Run: npm run serve
// ============================================================

import express, { Request, Response } from "express";
import cors from "cors";
import * as path from "path";
import * as dotenv from "dotenv";
import { InvestmentAgent } from "./agent/InvestmentAgent";
import { initFirebase } from "./services/FirestoreService";
import { lastModelUsed } from "./providers/ModelRouter";

dotenv.config();

const app = express();
const PORT = process.env.PORT ?? 3000;

// ── Middleware ────────────────────────────────────────────────
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

// ── Session store — one agent per browser session ─────────────
const sessions = new Map<string, InvestmentAgent>();

function getOrCreateAgent(sessionId: string): InvestmentAgent {
  if (!sessions.has(sessionId)) {
    const agent = new InvestmentAgent();
    agent.startSession();
    sessions.set(sessionId, agent);
    // Auto-expire after 2 hours of inactivity
    setTimeout(() => sessions.delete(sessionId), 2 * 60 * 60 * 1000);
  }
  return sessions.get(sessionId)!;
}

// ── POST /api/chat ─────────────────────────────────────────────
app.post("/api/chat", async (req: Request, res: Response) => {
  const { message, sessionId } = req.body as { message: string; sessionId?: string };

  if (!message?.trim()) {
    res.status(400).json({ error: "message is required" });
    return;
  }

  const sid = sessionId ?? `web_${Date.now()}`;

  try {
    const agent = getOrCreateAgent(sid);
    const response = await agent.chat_message(message);
    res.json({
      text: response.text,
      toolsUsed: response.toolsUsed,
      sessionId: sid,
      modelUsed: response.modelUsed
    });
  } catch (err) {
    const error = err as Error;
    console.error("[server] chat error:", error.message);
    res.status(500).json({ error: error.message });
  }
});

// ── POST /api/reset ────────────────────────────────────────────
app.post("/api/reset", (req: Request, res: Response) => {
  const { sessionId } = req.body as { sessionId?: string };
  if (sessionId) {
    sessions.delete(sessionId);
  }
  const newId = `web_${Date.now()}`;
  res.json({ sessionId: newId, message: "Session reset." });
});

// ── GET /api/status ────────────────────────────────────────────
app.get("/api/status", (_req: Request, res: Response) => {
  res.json({
    status: "ok",
    activeSessions: sessions.size,
    model: "gemini-2.5-flash",
    activeModel: lastModelUsed,
    timestamp: new Date().toISOString()
  });
});

// ── GET /api/health ────────────────────────────────────────────
app.get("/api/health", (_req: Request, res: Response) => {
  const hasGeminiKey = !!process.env.GEMINI_API_KEY;
  res.json({
    status: hasGeminiKey ? "ok" : "degraded",
    checks: {
      geminiApiKey: hasGeminiKey ? "present" : "missing",
      activeSessions: sessions.size,
      uptime: Math.round(process.uptime()) + "s"
    }
  });
});

// ── Catch-all → serve index.html ──────────────────────────────
app.get("/{*path}", (_req: Request, res: Response) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

// ── Start ─────────────────────────────────────────────────────
async function start(): Promise<void> {
  try {
    initFirebase();
  } catch {
    console.log("⚠  Firestore offline — running with local data");
  }

  app.listen(PORT, () => {
    console.log(`
╔══════════════════════════════════════════════════════╗
║  AI Investment Co-pilot — Web UI                     ║
╚══════════════════════════════════════════════════════╝
  Open in browser → http://localhost:${PORT}
  Press Ctrl+C to stop
`);
  });
}

start().catch(console.error);
