// ============================================================
// InsightService — AI-powered weekly investment insight generator
// Calls Gemini 2.5 Flash directly (NOT via agent loop)
// ============================================================

import * as dotenv from "dotenv";
dotenv.config();

import crypto from "crypto";
import { GoogleGenerativeAI } from "@google/generative-ai";
import { UserProfile } from "../models/UserProfile";
import { getDb } from "./FirestoreService";

// ── Types ─────────────────────────────────────────────────────

export interface WeeklyInsight {
  id: string;
  uid: string;
  weekNumber: number;
  year: number;
  title: string;
  summary: string;               // 2-3 sentence overview
  marketContext: string;         // What happened in markets this week (general)
  portfolioRelevance: string;    // How it affects Nitish specifically
  actionItem: string;            // ONE concrete action for Nitish this week
  riskReminder: string;          // One risk reminder relevant to his profile
  generatedAt: string;
}

// ── ISO week number helper ────────────────────────────────────

export function getWeekNumber(date: Date): number {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
}

// ── Fallback insight (returned when Gemini is unavailable) ────

function buildFallbackInsight(uid: string): WeeklyInsight {
  const now = new Date();
  return {
    id: crypto.randomUUID(),
    uid,
    weekNumber: getWeekNumber(now),
    year: now.getFullYear(),
    title: "Stay the Course — Your Weekly Check-In",
    summary:
      "Markets move constantly, but your long-term FIRE plan at €600k by age 47 is built on consistency, not short-term noise. Your current surplus of ~€2,810/month is your most powerful asset. Keep investing systematically.",
    marketContext:
      "Market data temporarily unavailable. Check major indices (MSCI World, DAX) via your broker app for the latest weekly performance.",
    portfolioRelevance:
      "You are currently 100% in cash and gold. Any market movement this week does not yet affect your equity exposure — but it is a reminder that your uninvested cash is missing out on long-run equity returns.",
    actionItem:
      "Review your Scalable Capital Tagesgeld rate (currently 2% p.a.). Compare with Tagesgeld Vergleich portals — several German banks offer 3%+ right now. Moving €20k could earn you an extra €200/year risk-free.",
    riskReminder:
      "As a beginner-level investor with a 'hold but stressed' risk profile, do not react to short-term market drops. Your 13-year FIRE runway absorbs volatility — temporary drawdowns are normal and expected.",
    generatedAt: now.toISOString(),
  };
}

// ── Gemini prompt ─────────────────────────────────────────────

function buildPrompt(profile: UserProfile): string {
  const now = new Date();
  const weekNum = getWeekNumber(now);
  const year = now.getFullYear();

  return `You are a financial insight generator for a personal investment agent.

Generate a concise, personalised weekly investment insight for the following investor. Return ONLY valid JSON matching the schema exactly — no markdown, no extra text.

INVESTOR PROFILE:
- Name: ${profile.firstName}, Age ${profile.age}, Ingolstadt Germany
- FIRE goal: €${profile.fireNumber.toLocaleString()} by age ${profile.fireTargetAge} (${profile.fireTargetYear})
- Monthly surplus to invest: €${profile.monthlySurplus.toFixed(0)}
- Current net worth: €${profile.netWorth.toLocaleString()}
- Risk profile: Hold but stressed (moderate, beginner level)
- Investment style: Hybrid (80% passive ETF core + 20% satellite)
- Tax: Steuerklasse III, Freistellungsauftrag €2,000 (married), files Steuererklärung
- Current situation: Heavily cash-positioned (no equity ETFs yet), €4,712 EUWAX Gold II hedge
- Key gap: Tagesgeld at 2% p.a. is below market rate
- Context: Week ${weekNum} of ${year}

OUTPUT SCHEMA (JSON only, max 300 tokens total):
{
  "title": "short punchy weekly headline (max 10 words)",
  "summary": "2-3 sentences: what matters most for Nitish this week",
  "marketContext": "1-2 sentences: what happened in global markets this week (general trends, not specific numbers you cannot verify)",
  "portfolioRelevance": "1-2 sentences: how market context specifically affects Nitish's cash-heavy, gold-holding position",
  "actionItem": "ONE concrete, specific action Nitish can take THIS week (be direct and opinionated)",
  "riskReminder": "ONE sentence reminding Nitish of a risk relevant to his profile and current position"
}`;
}

// ── Generate insight via Gemini ───────────────────────────────

export async function generateWeeklyInsight(profile: UserProfile): Promise<WeeklyInsight> {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    console.warn("[InsightService] GEMINI_API_KEY not set — returning fallback insight.");
    return buildFallbackInsight(profile.uid);
  }

  try {
    const genAI = new GoogleGenerativeAI(apiKey);
    const model = genAI.getGenerativeModel({
      model: "gemini-2.5-flash",
      generationConfig: {
        responseMimeType: "application/json",
        maxOutputTokens: 300,
      },
    });

    const result = await model.generateContent(buildPrompt(profile));
    const text = result.response.text();

    let parsed: {
      title: string;
      summary: string;
      marketContext: string;
      portfolioRelevance: string;
      actionItem: string;
      riskReminder: string;
    };

    try {
      parsed = JSON.parse(text);
    } catch {
      console.warn("[InsightService] Failed to parse Gemini JSON response — returning fallback.");
      return buildFallbackInsight(profile.uid);
    }

    const now = new Date();
    return {
      id: crypto.randomUUID(),
      uid: profile.uid,
      weekNumber: getWeekNumber(now),
      year: now.getFullYear(),
      title: parsed.title ?? "Weekly Investment Insight",
      summary: parsed.summary ?? "",
      marketContext: parsed.marketContext ?? "",
      portfolioRelevance: parsed.portfolioRelevance ?? "",
      actionItem: parsed.actionItem ?? "",
      riskReminder: parsed.riskReminder ?? "",
      generatedAt: now.toISOString(),
    };
  } catch (err) {
    console.warn("[InsightService] Gemini call failed:", err);
    return buildFallbackInsight(profile.uid);
  }
}

// ── Firestore persistence ─────────────────────────────────────

export async function saveInsight(uid: string, insight: WeeklyInsight): Promise<void> {
  try {
    const db = getDb();
    await db
      .collection("users")
      .doc(uid)
      .collection("insights")
      .doc(insight.id)
      .set(insight);
  } catch { /* offline — skip */ }
}

export async function getLatestInsight(uid: string): Promise<WeeklyInsight | null> {
  try {
    const db = getDb();
    const snapshot = await db
      .collection("users")
      .doc(uid)
      .collection("insights")
      .orderBy("generatedAt", "desc")
      .limit(1)
      .get();

    if (snapshot.empty) return null;
    return snapshot.docs[0].data() as WeeklyInsight;
  } catch {
    return null;
  }
}
