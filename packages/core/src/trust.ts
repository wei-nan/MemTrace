/**
 * Trust Scoring Logic
 * 
 * Implements the composite trust score calculation for memory nodes.
 * Weights:
 * - Accuracy: 40%
 * - Freshness: 25%
 * - Utility: 25%
 * - Author Reputation: 10%
 */

export interface TrustDimensions {
  accuracy: number;
  freshness: number;
  utility: number;
  authorRep: number;
}

export function computeTrustScore(dims: TrustDimensions): number {
  return (
    dims.accuracy * 0.40 +
    dims.freshness * 0.25 +
    dims.utility * 0.25 +
    dims.authorRep * 0.10
  );
}

/**
 * Partial update logic: merges new dimensions with current ones and recomputes score.
 */
export function updateTrustScore(
  current: TrustDimensions,
  updates: Partial<TrustDimensions>
): { score: number; dims: TrustDimensions } {
  const next: TrustDimensions = {
    accuracy: updates.accuracy ?? current.accuracy,
    freshness: updates.freshness ?? current.freshness,
    utility: updates.utility ?? current.utility,
    authorRep: updates.authorRep ?? current.authorRep,
  };

  return {
    score: computeTrustScore(next),
    dims: next,
  };
}
