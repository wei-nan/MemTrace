import type { RelationType } from "./types";

/**
 * Calculates the new weight based on decay formula.
 * weight(t) = w0_current * (0.5 ^ (days_since_last_access / half_life))
 */
export function calculateDecayedWeight(
  currentWeight: number,
  lastCoAccessed: Date | string,
  halfLifeDays: number
): number {
  const lastAcc = new Date(lastCoAccessed);
  const now = new Date();
  const daysSinceUse = (now.getTime() - lastAcc.getTime()) / (24 * 60 * 60 * 1000);

  if (daysSinceUse <= 0) return currentWeight;

  return currentWeight * Math.pow(0.5, daysSinceUse / halfLifeDays);
}

/**
 * Returns the co-access weight boost for a given relation type.
 * Mirrors the boost values in SPEC §7 and SQL record_co_access().
 */
export function coAccessBoost(relation: RelationType): number {
  const boosts: Record<RelationType, number> = {
    depends_on:  0.30,
    extends:     0.20,
    related_to:  0.15,
    contradicts: 0.10,
  };
  return boosts[relation] ?? 0.10;
}

/**
 * Applies co-access boost and clamps result to [0, 1].
 */
export function applyCoAccessBoost(currentWeight: number, relation: RelationType): number {
  return Math.min(1.0, currentWeight + coAccessBoost(relation));
}

/**
 * Checks if a weight has decayed below the minimum threshold.
 */
export function isWeightBelowThreshold(weight: number, minWeight: number): boolean {
  return weight < minWeight;
}
