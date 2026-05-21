// ============================================================
// NotificationTriggers — 7 notification types
// Each generates a Notification object to store/display
// ============================================================

import crypto from "crypto";
import { Notification, NotificationType } from "../models/Notification";
import { UserProfile } from "../models/UserProfile";
import { Portfolio, RebalanceResult } from "../models/Portfolio";

export class NotificationTriggers {

  // NT-01: Portfolio drifted >5% from target
  rebalanceAlert(uid: string, result: RebalanceResult): Notification | null {
    if (!result.needsRebalancing) return null;
    const worstDrift = result.drifts.reduce((max, d) =>
      Math.abs(d.driftPercent) > Math.abs(max.driftPercent) ? d : max
    );
    return this.build(uid, "NT01_REBALANCE_ALERT", {
      title: `Rebalance needed — ${worstDrift.label} drifted ${worstDrift.driftPercent > 0 ? "+" : ""}${worstDrift.driftPercent}%`,
      body: `Your ${worstDrift.label} is at ${worstDrift.currentPercent}% (target: ${worstDrift.targetPercent}%). ${result.drifts.filter(d => d.actionRequired !== "hold").length} position(s) need adjustment.`,
      actionLabel: "View rebalancing plan",
      actionRoute: "/portfolio/rebalance"
    });
  }

  // NT-02: Monthly contribution reminder (3rd of month)
  contributionReminder(uid: string, monthlyAmount: number): Notification {
    const month = new Date().toLocaleString("en-DE", { month: "long" });
    return this.build(uid, "NT02_CONTRIBUTION_REMINDER", {
      title: `${month} investment day — €${monthlyAmount.toLocaleString("de-DE")} ready to deploy?`,
      body: `Your monthly investment of €${monthlyAmount.toLocaleString("de-DE")} is due. Confirm to log contribution or skip this month.`,
      actionLabel: "Confirm contribution",
      actionRoute: "/portfolio/contribute"
    });
  }

  // NT-03: Portfolio dropped >10% in 30 days
  marketDropAlert(uid: string, portfolioDropPercent: number, portfolioValueEur: number): Notification {
    return this.build(uid, "NT03_MARKET_DROP_ALERT", {
      title: `Portfolio down ${portfolioDropPercent.toFixed(1)}% — stay the course`,
      body: `Your portfolio is down ${portfolioDropPercent.toFixed(1)}% (€${portfolioValueEur.toLocaleString("de-DE")}) this month. This is normal. Selling now locks in losses. Long-term investors buy here.`,
      actionLabel: "View stay-the-course guide",
      actionRoute: "/insights/market-drop"
    });
  }

  // NT-04: Tax filing deadline (30 days before July 31)
  taxDeadlineReminder(uid: string, deadlineDate: string): Notification {
    const daysLeft = Math.ceil(
      (new Date(deadlineDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
    );
    return this.build(uid, "NT04_TAX_DEADLINE", {
      title: `Steuererklärung due in ${daysLeft} days — export broker statements now`,
      body: `German tax deadline: ${new Date(deadlineDate).toLocaleDateString("de-DE")}. Export your Jahressteuerbescheinigung from Scalable Capital and prepare Anlage KAP.`,
      actionLabel: "Open tax checklist",
      actionRoute: "/tax/checklist"
    });
  }

  // NT-05: Vorabpauschale notice (1 January)
  vorabpauschaleNotice(uid: string, estimatedTaxEur: number, fundNames: string[]): Notification {
    return this.build(uid, "NT05_VORABPAUSCHALE_NOTICE", {
      title: `Vorabpauschale ${new Date().getFullYear()} — ensure €${estimatedTaxEur.toFixed(2)} cash available`,
      body: `Accumulating ETFs (${fundNames.join(", ")}) trigger Vorabpauschale. Scalable Capital will deduct ~€${estimatedTaxEur.toFixed(2)} from your cash account in January. Ensure sufficient balance.`,
      actionLabel: "View calculation breakdown",
      actionRoute: "/tax/vorabpauschale"
    });
  }

  // NT-06: Weekly AI insight (Monday 9AM)
  weeklyInsight(uid: string, insightTitle: string, insightBody: string): Notification {
    return this.build(uid, "NT06_WEEKLY_INSIGHT", {
      title: `Weekly insight: ${insightTitle}`,
      body: insightBody,
      actionLabel: "Read full insight",
      actionRoute: "/insights/weekly"
    });
  }

  // NT-07: Goal milestone (25%, 50%, 75%, 100% of FIRE target)
  goalMilestone(uid: string, currentValue: number, targetValue: number): Notification | null {
    const percent = (currentValue / targetValue) * 100;
    const milestones = [25, 50, 75, 100];

    for (const milestone of milestones) {
      if (percent >= milestone && percent < milestone + 1) {
        return this.build(uid, "NT07_GOAL_MILESTONE", {
          title: `🎯 ${milestone}% of FIRE goal reached!`,
          body: `Your portfolio has reached €${currentValue.toLocaleString("de-DE")} — ${milestone}% of your €${targetValue.toLocaleString("de-DE")} FIRE target. ${milestone === 100 ? "You did it!" : "Keep going!"}`,
          actionLabel: "View goal tracker",
          actionRoute: "/goals/fire"
        });
      }
    }
    return null;
  }

  private build(
    uid: string,
    type: NotificationType,
    content: { title: string; body: string; actionLabel: string; actionRoute: string }
  ): Notification {
    return {
      id: crypto.randomUUID(),
      uid,
      type,
      ...content,
      data: {},
      status: "pending",
      createdAt: new Date().toISOString()
    };
  }
}
