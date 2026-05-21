// ============================================================
// Notification — 7 FCM notification types
// ============================================================

export type NotificationType =
  | "NT01_REBALANCE_ALERT"
  | "NT02_CONTRIBUTION_REMINDER"
  | "NT03_MARKET_DROP_ALERT"
  | "NT04_TAX_DEADLINE"
  | "NT05_VORABPAUSCHALE_NOTICE"
  | "NT06_WEEKLY_INSIGHT"
  | "NT07_GOAL_MILESTONE";

export type NotificationStatus = "pending" | "sent" | "read" | "dismissed";

export interface Notification {
  id: string;
  uid: string;
  type: NotificationType;
  title: string;
  body: string;
  actionLabel: string;
  actionRoute: string;            // deep link: "/rebalance", "/goals", etc.
  data?: Record<string, string>;  // extra payload
  status: NotificationStatus;
  createdAt: string;
  sentAt?: string;
  readAt?: string;
}

export interface NotificationSettings {
  uid: string;
  NT01_REBALANCE_ALERT: boolean;
  NT02_CONTRIBUTION_REMINDER: boolean;
  NT03_MARKET_DROP_ALERT: boolean;
  NT04_TAX_DEADLINE: boolean;
  NT05_VORABPAUSCHALE_NOTICE: boolean;
  NT06_WEEKLY_INSIGHT: boolean;
  NT07_GOAL_MILESTONE: boolean;
  quietHoursStart: number;        // hour 0–23, e.g. 22
  quietHoursEnd: number;          // hour 0–23, e.g. 8
  rebalanceDriftThreshold: number; // %, default 5
  contributionReminderDay: number; // day of month, default 3
  marketDropThreshold: number;    // %, default 10
  updatedAt: string;
}
