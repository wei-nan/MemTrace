import type { RelationType, ContentType } from "./types";
// Re-export ContentType for convenience so callers can import from this module
export type { ContentType } from "./types";

export type KbType = "evergreen" | "operational" | "ephemeral";

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
    depends_on:       0.30,
    extends:          0.20,
    related_to:       0.15,
    contradicts:      0.10,
    answered_by:      0.25,
    similar_to:       0.12,
    queried_via_mcp:  0.08,
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

/**
 * Returns the half_life_days for a given content_type and kb_type.
 * evergreen: factual=365, procedural=180, preference=90, context=60
 * operational: factual=365, procedural=180, preference=90, context=60 (same as evergreen)
 * ephemeral:  factual=30,  procedural=14,  preference=7,  context=3
 */
export function contentTypeHalfLife(contentType: ContentType, kbType: KbType): number {
  if (kbType === "ephemeral") {
    const halfLives: Record<ContentType, number> = {
      factual:    30,
      procedural: 14,
      preference:  7,
      context:     3,
      inquiry:     7,  // inquiry nodes decay at same rate as preference in ephemeral KBs
    };
    return halfLives[contentType] ?? 14;
  }
  // evergreen and operational share the same long-lived defaults
  const halfLives: Record<ContentType, number> = {
    factual:    365,
    procedural: 180,
    preference:  90,
    context:     60,
    inquiry:     30,  // inquiry nodes have shorter half-life even in evergreen KBs
  };
  return halfLives[contentType] ?? 180;
}
