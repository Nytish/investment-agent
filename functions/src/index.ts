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
