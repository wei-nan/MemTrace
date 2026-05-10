// ─── @memtrace/core public API ──────────────────────────────────────────────
// Explicit named re-exports to avoid duplicate export errors between modules.
// types.ts is the canonical source for shared types; decay.ts re-exports from types.

// From types.ts — canonical shared types
export type {
  ContentType,
  ContentFormat,
  Visibility,
  SourceType,
  MemoryNodeTitle,
  MemoryNodeBody,
  MemoryNodeContent,
  MemoryNodeProvenance,
  TrustDimensions,
  TrustVotes,
  MemoryNodeTrust,
  MemoryNodeTraversal,
  MemoryNode,
  RelationType,
  EdgeDecay,
  EdgeTraversal,
  Edge,
} from "./types";

export {
  DEFAULT_TRUST,
  DEFAULT_TRAVERSAL_NODE,
  DEFAULT_TRAVERSAL_EDGE,
  DEFAULT_DECAY,
  composeTrustScore,
} from "./types";

// From decay.ts — KbType is unique to decay; avoid re-exporting ContentType (comes from types)
export type { KbType } from "./decay";
export {
  calculateDecayedWeight,
  coAccessBoost,
  applyCoAccessBoost,
  isWeightBelowThreshold,
  contentTypeHalfLife,
} from "./decay";

// From schema.ts
export { validateNode, validateEdge, verifyNodeSignature } from "./schema";

// From id.ts
export * from "./id";

// From trust.ts — TrustDimensions here has different shape (camelCase fields for CLI usage)
// Exported with distinct names to avoid conflict with types.ts TrustDimensions
export type { TrustDimensions as TrustDimensionsLocal } from "./trust";
export { computeTrustScore, updateTrustScore } from "./trust";
