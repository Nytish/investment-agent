// ============================================================
// Firebase Cloud Functions — Scheduled Notification Triggers
// Deployed once. Runs automatically in the cloud.
// ============================================================

import { onSchedule } from "firebase-functions/v2/scheduler";
import * as admin from "firebase-admin";
import * as crypto from "crypto";

admin.initializeApp();
const db = admin.firestore();

const NITISH_UID = "nitish_bidwe";

// ── NT-02: Monthly contribution reminder (3rd of each month, 9AM Berlin) ──

export const contributionReminder = onSchedule(
  {
    schedule: "0 9 3 * *",        // 3rd day, 9:00 AM
    timeZone: "Europe/Berlin",
    region: "europe-west1"
  },
  async () => {
    const profileDoc = await db
      .collection("users").doc(NITISH_UID)
      .collection("data").doc("profile")
      .get();

    if (!profileDoc.exists) return;
    const profile = profileDoc.data()!;
    const monthlyAmount = profile.monthlySurplus ?? 2000;
    const month = new Date().toLocaleString("de-DE", { month: "long" });

    await saveNotification(NITISH_UID, {
      type: "NT02_CONTRIBUTION_REMINDER",
      title: `${month}: €${monthlyAmount.toLocaleString("de-DE")} investieren?`,
      body: `Dein monatlicher Investitionstag. Möchtest du €${monthlyAmount.toLocaleString("de-DE")} einzahlen?`,
      actionLabel: "Beitrag bestätigen",
      actionRoute: "/portfolio/contribute"
    });
  }
);

// ── NT-04: Tax deadline — 30 days before July 31 (July 1st, 9AM) ──

export const taxDeadlineReminder = onSchedule(
  {
    schedule: "0 9 1 7 *",        // July 1st, 9:00 AM
    timeZone: "Europe/Berlin",
    region: "europe-west1"
  },
  async () => {
    const year = new Date().getFullYear();
    await saveNotification(NITISH_UID, {
      type: "NT04_TAX_DEADLINE",
      title: `Steuererklärung ${year - 1}: 30 Tage bis 31. Juli`,
      body: `Jetzt Jahressteuerbescheinigung von Scalable Capital exportieren. Anlage KAP vorbereiten. Vorabpauschale prüfen.`,
      actionLabel: "Steuer-Checkliste öffnen",
      actionRoute: "/tax/checklist"
    });
  }
);

// ── NT-05: Vorabpauschale notice — January 1st, 8AM ──

export const vorabpauschaleNotice = onSchedule(
  {
    schedule: "0 8 1 1 *",        // January 1st, 8:00 AM
    timeZone: "Europe/Berlin",
    region: "europe-west1"
  },
  async () => {
    const year = new Date().getFullYear();

    // Estimate based on known holdings (update as portfolio grows)
    // Basiszins 2026 ~2.10%, VWCE holding example
    const estimatedVorabpauschale = 85;   // EUR — update based on actual portfolio

    await saveNotification(NITISH_UID, {
      type: "NT05_VORABPAUSCHALE_NOTICE",
      title: `Vorabpauschale ${year}: ca. €${estimatedVorabpauschale} fällig`,
      body: `Scalable Capital zieht die Vorabpauschale automatisch ab. Stelle sicher, dass genug Cash im Konto ist. Freistellungsauftrag (€2.000) wird zuerst angerechnet.`,
      actionLabel: "Berechnung anzeigen",
      actionRoute: "/tax/vorabpauschale"
    });
  }
);

// ── NT-06: Weekly insight — every Monday, 9AM ──

export const weeklyInsightReminder = onSchedule(
  {
    schedule: "0 9 * * 1",        // Every Monday, 9:00 AM
    timeZone: "Europe/Berlin",
    region: "europe-west1"
  },
  async () => {
    const weekNumber = getWeekNumber(new Date());

    await saveNotification(NITISH_UID, {
      type: "NT06_WEEKLY_INSIGHT",
      title: `Wochenrückblick KW${weekNumber}: Portfolio-Update verfügbar`,
      body: `Dein wöchentliches Investment-Update ist bereit. Marktkommentar + 1 konkrete Handlungsempfehlung.`,
      actionLabel: "Insight lesen",
      actionRoute: "/insights/weekly"
    });
  }
);

// ── NT-03: Rebalancing check — every Saturday 10AM Berlin ──

export const rebalancingCheck = onSchedule(
  {
    schedule: "0 10 * * 6",       // Every Saturday, 10:00 AM
    timeZone: "Europe/Berlin",
    region: "europe-west1"
  },
  async () => {
    const portfolioDoc = await db
      .collection("users").doc(NITISH_UID)
      .collection("data").doc("portfolio")
      .get();

    if (!portfolioDoc.exists) return;

    const portfolio = portfolioDoc.data()!;
    const holdings: Array<{ ticker: string; value: number; assetClass: string }> = portfolio.holdings ?? [];

    if (holdings.length === 0) return;

    const totalValue = holdings.reduce((sum, h) => sum + h.value, 0);
    if (totalValue === 0) return;

    // Target allocations (balanced portfolio)
    const targets: Record<string, number> = {
      "VWCE": 55, "IS3N": 15, "GOLD": 10, "IWDP": 10, "CASH": 10
    };

    const drifts: string[] = [];
    for (const holding of holdings) {
      const ticker = holding.ticker?.toUpperCase() ?? "";
      const target = targets[ticker];
      if (target === undefined) continue;
      const actual = (holding.value / totalValue) * 100;
      const drift = Math.abs(actual - target);
      if (drift > 5) {
        const direction = actual > target ? "übergewichtet" : "untergewichtet";
        drifts.push(`${ticker}: ${actual.toFixed(1)}% (Ziel ${target}%, ${direction} um ${drift.toFixed(1)}%)`);
      }
    }

    if (drifts.length === 0) return;   // Portfolio on track — no notification

    await saveNotification(NITISH_UID, {
      type: "NT03_REBALANCE_NEEDED",
      title: `Rebalancing empfohlen: ${drifts.length} Position(en) abgewichen`,
      body: `Portfolio-Drift erkannt: ${drifts.join(", ")}. Rebalancing unter €2.000 Freistellungsauftrag prüfen.`,
      actionLabel: "Rebalancing planen",
      actionRoute: "/portfolio/rebalance"
    });
  }
);

// ── NT-01: Market drop monitor — weekdays 8AM Berlin ──

export const marketDropMonitor = onSchedule(
  {
    schedule: "0 8 * * 1-5",      // Weekdays, 8:00 AM
    timeZone: "Europe/Berlin",
    region: "europe-west1"
  },
  async () => {
    // Check for manually-triggered market alert
    const alertDoc = await db
      .collection("users").doc(NITISH_UID)
      .collection("data").doc("marketAlert")
      .get();

    if (!alertDoc.exists) return;

    const alert = alertDoc.data()!;
    if (!alert.triggerDrop) return;

    const dropPercent = alert.dropPercent ?? 5;
    const indexName = alert.indexName ?? "MSCI World";

    await saveNotification(NITISH_UID, {
      type: "NT01_MARKET_DROP",
      title: `Marktkorrektur: ${indexName} -${dropPercent}%`,
      body: `${indexName} ist um ${dropPercent}% gefallen. Dein Sparplan läuft weiter — günstigere Einkaufspreise für VWCE. Nachkaufen? Rebalancing prüfen.`,
      actionLabel: "Portfolio analysieren",
      actionRoute: "/portfolio/analysis"
    });

    // Reset the trigger so it doesn't fire repeatedly
    await db
      .collection("users").doc(NITISH_UID)
      .collection("data").doc("marketAlert")
      .update({ triggerDrop: false, lastTriggeredAt: new Date().toISOString() });
  }
);

// ── Helper functions ──────────────────────────────────────────

async function saveNotification(
  uid: string,
  content: {
    type: string;
    title: string;
    body: string;
    actionLabel: string;
    actionRoute: string;
  }
): Promise<void> {
  const notification = {
    id: crypto.randomUUID(),
    uid,
    ...content,
    status: "pending",
    createdAt: new Date().toISOString()
  };

  await db
    .collection("users")
    .doc(uid)
    .collection("notifications")
    .doc(notification.id)
    .set(notification);
}

function getWeekNumber(date: Date): number {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
}
