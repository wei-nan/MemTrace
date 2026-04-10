/**
 * Calculates the new weight based on decay formula.
 *
 * weight(t) = w0_current * (0.5 ^ (days_since_last_access / half_life))
 *
 * @param currentWeight The weight at the last co-access time
 * @param lastCoAccessed Date of the last co-access
 * @param halfLifeDays The half-life in days for decay
 * @returns new weight
 */
export function calculateDecayedWeight(
  currentWeight: number,
  lastCoAccessed: Date | string,
  halfLifeDays: number
): number {
  const lastAcc = new Date(lastCoAccessed);
  const now = new Date();

  // Convert to days
  const msInDay = 24 * 60 * 60 * 1000;
  const daysSinceUse = (now.getTime() - lastAcc.getTime()) / msInDay;

  if (daysSinceUse <= 0) {
    return currentWeight;
  }

  const factor = Math.pow(0.5, daysSinceUse / halfLifeDays);
  return currentWeight * factor;
}

/**
 * Checks if a weight has decayed below the minimum threshold.
 */
export function isWeightBelowThreshold(weight: number, minWeight: number): boolean {
  return weight < minWeight;
}
