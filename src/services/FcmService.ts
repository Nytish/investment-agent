// ============================================================
// FcmService — Firebase Cloud Messaging push notifications
// Graceful: skips silently if no FCM token registered
// ============================================================

import * as admin from "firebase-admin";
import { getDb } from "./FirestoreService";

export interface FcmPayload {
  title: string;
  body: string;
  data?: Record<string, string>;
}

// Get stored FCM token for a user (may not exist for CLI users)
export async function getFcmToken(uid: string): Promise<string | null> {
  try {
    const db = getDb();
    const doc = await db.collection("users").doc(uid).collection("data").doc("fcmToken").get();
    return doc.exists ? (doc.data()?.token as string ?? null) : null;
  } catch {
    return null;
  }
}

// Save an FCM token for a user (called when mobile/web app registers)
export async function saveFcmToken(uid: string, token: string): Promise<void> {
  try {
    const db = getDb();
    await db.collection("users").doc(uid).collection("data").doc("fcmToken").set({
      token,
      updatedAt: new Date().toISOString()
    });
  } catch { /* offline — skip */ }
}

// Send a push notification — silently skips if no token or FCM unavailable
export async function sendPushNotification(uid: string, payload: FcmPayload): Promise<boolean> {
  try {
    const token = await getFcmToken(uid);
    if (!token) return false;   // No token registered — CLI mode

    const message: admin.messaging.Message = {
      token,
      notification: {
        title: payload.title,
        body: payload.body
      },
      data: payload.data ?? {},
      android: {
        priority: "high",
        notification: { channelId: "investment_alerts" }
      },
      apns: {
        payload: { aps: { sound: "default" } }
      }
    };

    await admin.messaging().send(message);
    return true;
  } catch {
    return false;   // FCM failure — non-fatal
  }
}
