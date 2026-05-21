// ============================================================
// Notification Tools — Gemini function declarations + executors
// ============================================================

import { FunctionDeclaration, SchemaType } from "@google/generative-ai";
import { getRecentNotifications, saveNotification, getNotificationSettings } from "../services/FirestoreService";
import { NITISH_UID, NITISH_PROFILE } from "../services/SeedData";
import { getDb, isFirestoreAvailable } from "../services/FirestoreService";

export const NOTIFICATION_TOOL_DECLARATIONS: FunctionDeclaration[] = [
  {
    name: "getNotifications",
    description: "Fetch Nitish's recent notifications and alerts. Returns unread investment reminders, tax deadlines, rebalancing alerts, and weekly insights.",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {
        limit: {
          type: SchemaType.NUMBER,
          description: "Max notifications to return (default 10, max 30)"
        },
        unreadOnly: {
          type: SchemaType.BOOLEAN,
          description: "If true, return only unread notifications"
        }
      },
      required: []
    }
  },
  {
    name: "markNotificationRead",
    description: "Mark a specific notification as read by its ID.",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {
        notificationId: {
          type: SchemaType.STRING,
          description: "The notification ID to mark as read"
        }
      },
      required: ["notificationId"]
    }
  },
  {
    name: "getNotificationSettings",
    description: "Get Nitish's notification preferences — which alert types are enabled, preferred times, and channels.",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {},
      required: []
    }
  }
];

export async function executeNotificationTool(name: string, args: Record<string, unknown>): Promise<unknown> {
  switch (name) {
    case "getNotifications": {
      const limit = Math.min((args.limit as number) ?? 10, 30);
      const unreadOnly = (args.unreadOnly as boolean) ?? false;

      const notifications = await getRecentNotifications(NITISH_UID, limit);

      if (notifications.length === 0) {
        return {
          count: 0,
          message: "No notifications found.",
          notifications: []
        };
      }

      const filtered = unreadOnly
        ? notifications.filter(n => n.status !== "read")
        : notifications;

      return {
        count: filtered.length,
        unreadCount: notifications.filter(n => n.status !== "read").length,
        notifications: filtered.map(n => ({
          id: n.id,
          type: n.type,
          title: n.title,
          body: n.body,
          status: n.status,
          createdAt: n.createdAt,
          isUnread: n.status !== "read"
        }))
      };
    }

    case "markNotificationRead": {
      const notificationId = args.notificationId as string;
      if (!notificationId) {
        return { success: false, error: "notificationId is required" };
      }

      if (!isFirestoreAvailable()) {
        return { success: false, error: "Firestore offline — cannot update notification" };
      }

      try {
        const db = getDb();
        await db
          .collection("users").doc(NITISH_UID)
          .collection("notifications").doc(notificationId)
          .update({ status: "read", readAt: new Date().toISOString() });

        return { success: true, notificationId, message: "Notification marked as read." };
      } catch {
        return { success: false, error: "Failed to update notification" };
      }
    }

    case "getNotificationSettings": {
      const settings = await getNotificationSettings(NITISH_UID);

      if (!settings) {
        return {
          found: false,
          message: "No custom notification settings found. Using defaults.",
          defaults: {
            contributionReminder: true,   // 3rd of month
            taxDeadlineReminder: true,    // July 1st
            vorabpauschaleNotice: true,   // January 1st
            weeklyInsight: true,          // Every Monday
            rebalanceAlert: true,         // When drift > 5%
            marketDropAlert: true         // When market drops > 5%
          }
        };
      }

      return {
        found: true,
        settings
      };
    }

    default:
      return { error: `Unknown notification tool: ${name}` };
  }
}
