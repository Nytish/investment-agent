// ============================================================
// HoldingsService — portfolio holdings CRUD + analytics
// Offline-safe: falls back to in-memory localHoldings when
// Firestore is unavailable.
// ============================================================

import crypto from "crypto";
import { Holding } from "../models/Portfolio";
import { getDb, isFirestoreAvailable } from "./FirestoreService";
import { NITISH_UID } from "./SeedData";

// Suppress unused-variable lint warning — NITISH_UID is re-exported
// for consumers and used as the default uid in getPortfolioValueEur.
void NITISH_UID;

// ── In-memory fallback store ──────────────────────────────────

let localHoldings: Holding[] = [
  {
    id: "euwax-gold-ii",
    name: "EUWAX Gold II",
    assetClass: "gold",
    isin: "DE000EWG2LD7",
    broker: "Scalable Capital",
    currentValue: 4712,
    purchaseDate: "2024-01-01",
    taxFreeAfter: "2025-01-01",
    notes: "Intentional gold hedge. Tax-free after 1yr (§23 EStG)."
  }
];

// ── Helpers ───────────────────────────────────────────────────

function holdingsCollection(uid: string) {
  return getDb().collection("users").doc(uid).collection("holdings");
}

// ── Public API ────────────────────────────────────────────────

/**
 * Returns all holdings for a user.
 * Uses Firestore when available, falls back to localHoldings otherwise.
 */
export async function getHoldings(uid: string): Promise<Holding[]> {
  if (!isFirestoreAvailable()) {
    return [...localHoldings];
  }
  try {
    const snapshot = await holdingsCollection(uid).get();
    if (snapshot.empty) {
      return [...localHoldings];
    }
    return snapshot.docs.map((doc) => doc.data() as Holding);
  } catch {
    return [...localHoldings];
  }
}

/**
 * Creates a new holding and persists it.
 * Always updates localHoldings as a local mirror.
 */
export async function addHolding(
  uid: string,
  holding: Omit<Holding, "id">
): Promise<Holding> {
  const newHolding: Holding = {
    ...holding,
    id: crypto.randomUUID()
  };

  // Update local cache
  localHoldings = [...localHoldings, newHolding];

  // Persist to Firestore if available
  if (isFirestoreAvailable()) {
    try {
      await holdingsCollection(uid).doc(newHolding.id).set(newHolding);
    } catch { /* offline — local cache already updated */ }
  }

  return newHolding;
}

/**
 * Updates specific fields of an existing holding by id.
 * Returns the updated holding or null if not found.
 */
export async function updateHolding(
  uid: string,
  holdingId: string,
  updates: Partial<Holding>
): Promise<Holding | null> {
  // Update local cache first
  let updatedHolding: Holding | null = null;
  localHoldings = localHoldings.map((h) => {
    if (h.id === holdingId) {
      updatedHolding = { ...h, ...updates, id: holdingId };
      return updatedHolding;
    }
    return h;
  });

  if (!updatedHolding) {
    // Not in local cache — try Firestore if available
    if (!isFirestoreAvailable()) return null;
    try {
      const ref = holdingsCollection(uid).doc(holdingId);
      const doc = await ref.get();
      if (!doc.exists) return null;
      const merged: Holding = { ...(doc.data() as Holding), ...updates, id: holdingId };
      await ref.set(merged);
      return merged;
    } catch {
      return null;
    }
  }

  // Persist update to Firestore
  if (isFirestoreAvailable()) {
    try {
      await holdingsCollection(uid).doc(holdingId).update(updates as Record<string, unknown>);
    } catch { /* offline — local cache already updated */ }
  }

  return updatedHolding;
}

/**
 * Removes a holding by id.
 * Returns true if the holding was found and removed.
 */
export async function deleteHolding(
  uid: string,
  holdingId: string
): Promise<boolean> {
  const before = localHoldings.length;
  localHoldings = localHoldings.filter((h) => h.id !== holdingId);
  const removedLocally = localHoldings.length < before;

  if (isFirestoreAvailable()) {
    try {
      const ref = holdingsCollection(uid).doc(holdingId);
      const doc = await ref.get();
      if (doc.exists) {
        await ref.delete();
        return true;
      }
    } catch { /* offline — fall through */ }
  }

  return removedLocally;
}

/**
 * Calculates portfolio totals and per-asset-class allocations.
 */
export function calculatePortfolioSummary(holdings: Holding[]): {
  totalValue: number;
  byAssetClass: Record<string, { value: number; percent: number }>;
  unrealizedGainTotal: number;
  holdingCount: number;
} {
  const totalValue = holdings.reduce((sum, h) => sum + h.currentValue, 0);

  const byAssetClass: Record<string, { value: number; percent: number }> = {};
  for (const h of holdings) {
    const key = h.assetClass;
    if (!byAssetClass[key]) {
      byAssetClass[key] = { value: 0, percent: 0 };
    }
    byAssetClass[key].value += h.currentValue;
  }

  // Calculate percentages after all values are summed
  for (const key of Object.keys(byAssetClass)) {
    byAssetClass[key].percent =
      totalValue > 0
        ? Math.round((byAssetClass[key].value / totalValue) * 10000) / 100
        : 0;
  }

  const unrealizedGainTotal = holdings.reduce(
    (sum, h) => sum + (h.unrealizedGain ?? 0),
    0
  );

  return {
    totalValue: Math.round(totalValue * 100) / 100,
    byAssetClass,
    unrealizedGainTotal: Math.round(unrealizedGainTotal * 100) / 100,
    holdingCount: holdings.length
  };
}

/**
 * Returns the total portfolio value in EUR for a given user.
 */
export async function getPortfolioValueEur(uid: string): Promise<number> {
  const holdings = await getHoldings(uid);
  return holdings.reduce((sum, h) => sum + h.currentValue, 0);
}
