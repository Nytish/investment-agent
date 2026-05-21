// ============================================================
// FirestoreService — all Firestore read/write operations
// ============================================================

import * as admin from "firebase-admin";
import * as path from "path";
import * as fs from "fs";
import * as dotenv from "dotenv";
import { UserProfile } from "../models/UserProfile";
import { Portfolio } from "../models/Portfolio";
import { Notification, NotificationSettings } from "../models/Notification";

dotenv.config();

let initialized = false;
let firestoreAvailable = false;

export function isFirestoreAvailable(): boolean {
  return firestoreAvailable;
}

export function initFirebase(): void {
  if (initialized) return;

  const projectId = process.env.FIREBASE_PROJECT_ID;
  const serviceAccountPath = process.env.FIREBASE_SERVICE_ACCOUNT_PATH;

  try {
  if (serviceAccountPath) {
    const resolved = path.resolve(serviceAccountPath);
    if (fs.existsSync(resolved)) {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const serviceAccount = require(resolved);
      admin.initializeApp({
        credential: admin.credential.cert(serviceAccount),
        projectId
      });
      initialized = true;
      firestoreAvailable = true;
      return;
    }
  }

  // Fallback: Application Default Credentials
  // Works after: gcloud auth application-default login
  admin.initializeApp({
    credential: admin.credential.applicationDefault(),
    projectId
  });
  initialized = true;
  firestoreAvailable = true;
  } catch {
    // No credentials available — run in offline mode
    initialized = true;
    firestoreAvailable = false;
  }
}

export function getDb(): admin.firestore.Firestore {
  if (!firestoreAvailable) {
    throw new Error("FIRESTORE_OFFLINE");
  }
  initFirebase();
  return admin.firestore();
}

// Graceful wrapper — never throws, returns null if offline
async function safeGet<T>(fn: () => Promise<T>): Promise<T | null> {
  try {
    return await fn();
  } catch {
    return null;
  }
}

// ── User Profile ─────────────────────────────────────────────

export async function getUserProfile(uid: string): Promise<UserProfile | null> {
  return safeGet(async () => {
    const db = getDb();
    const doc = await db.collection("users").doc(uid).collection("data").doc("profile").get();
    return doc.exists ? (doc.data() as UserProfile) : null;
  });
}

export async function saveUserProfile(profile: UserProfile): Promise<void> {
  try {
    const db = getDb();
    profile.updatedAt = new Date().toISOString();
    await db.collection("users").doc(profile.uid).collection("data").doc("profile").set(profile);
  } catch { /* offline — skip */ }
}

export async function updateUserProfile(uid: string, updates: Partial<UserProfile>): Promise<void> {
  try {
    const db = getDb();
    updates.updatedAt = new Date().toISOString();
    await db.collection("users").doc(uid).collection("data").doc("profile").update(updates);
  } catch { /* offline — skip */ }
}

// ── Portfolio ─────────────────────────────────────────────────

export async function getPortfolio(uid: string): Promise<Portfolio | null> {
  return safeGet(async () => {
    const db = getDb();
    const doc = await db.collection("users").doc(uid).collection("data").doc("portfolio").get();
    return doc.exists ? (doc.data() as Portfolio) : null;
  });
}

export async function savePortfolio(portfolio: Portfolio): Promise<void> {
  try {
    const db = getDb();
    portfolio.lastUpdated = new Date().toISOString();
    await db.collection("users").doc(portfolio.uid).collection("data").doc("portfolio").set(portfolio);
  } catch { /* offline — skip */ }
}

// ── Notifications ─────────────────────────────────────────────

export async function saveNotification(notification: Notification): Promise<void> {
  try {
    const db = getDb();
    await db.collection("users").doc(notification.uid)
      .collection("notifications").doc(notification.id).set(notification);
  } catch { /* offline — skip */ }
}

export async function getRecentNotifications(uid: string, limitCount = 30): Promise<Notification[]> {
  return (await safeGet(async () => {
    const db = getDb();
    const snapshot = await db.collection("users").doc(uid)
      .collection("notifications").orderBy("createdAt", "desc").limit(limitCount).get();
    return snapshot.docs.map((d) => d.data() as Notification);
  })) ?? [];
}

export async function getNotificationSettings(uid: string): Promise<NotificationSettings | null> {
  return safeGet(async () => {
    const db = getDb();
    const doc = await db.collection("users").doc(uid).collection("data").doc("notificationSettings").get();
    return doc.exists ? (doc.data() as NotificationSettings) : null;
  });
}

export async function saveNotificationSettings(settings: NotificationSettings): Promise<void> {
  try {
    const db = getDb();
    settings.updatedAt = new Date().toISOString();
    await db.collection("users").doc(settings.uid)
      .collection("data").doc("notificationSettings").set(settings);
  } catch { /* offline — skip */ }
}

// ── Conversation History ──────────────────────────────────────

export interface ConversationMessage {
  role: "user" | "model";
  content: string;
  timestamp: string;
}

export async function saveConversationMessage(uid: string, sessionId: string, message: ConversationMessage): Promise<void> {
  try {
    const db = getDb();
    await db.collection("users").doc(uid)
      .collection("conversations").doc(sessionId).collection("messages").add(message);
  } catch { /* offline — skip */ }
}

export async function getConversationHistory(uid: string, sessionId: string, limitCount = 20): Promise<ConversationMessage[]> {
  return (await safeGet(async () => {
    const db = getDb();
    const snapshot = await db.collection("users").doc(uid)
      .collection("conversations").doc(sessionId).collection("messages")
      .orderBy("timestamp", "asc").limit(limitCount).get();
    return snapshot.docs.map((d) => d.data() as ConversationMessage);
  })) ?? [];
}
