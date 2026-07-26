// ─── Memory Node ────────────────────────────────────────────────────────────

export type ContentType = "factual" | "procedural" | "preference" | "context" | "inquiry";
export type ContentFormat = "plain" | "markdown";
export type Visibility = "public" | "team" | "private";
export type SourceType = "human" | "ai_generated" | "ai_verified" | "document" | "qa_conversation" | "mcp";

export interface MemoryNodeTitle {
  "zh-TW": string;
  en: string;
}

export interface MemoryNodeBody {
  "zh-TW": string;
  en: string;
}

export interface MemoryNodeContent {
  type: ContentType;
  format: ContentFormat;
  body: MemoryNodeBody;
}

export interface MemoryNodeProvenance {
  author: string;
  created_at: string;           // ISO 8601
  signature: string;            // SHA-256 hex
  source_type: SourceType;
  updated_at?: string;          // ISO 8601 — set on edit
  source_document?: string;     // filename or SHA-256 of ingested file
  extraction_model?: string;    // AI model identifier
  copied_from?: {
    node_id: string;
    workspace_id: string;
  };
}

export interface MemoryNodeTraversal {
  count: number;
  unique_traversers: number;
}

export interface MemoryNode {
  id: string;
  schema_version: "1.0";
  title: MemoryNodeTitle;
  content: MemoryNodeContent;
  tags: string[];
  visibility: Visibility;
  provenance: MemoryNodeProvenance;
  traversal: MemoryNodeTraversal;
}

// ─── Edge ───────────────────────────────────────────────────────────────────

export type RelationType = "depends_on" | "extends" | "related_to" | "contradicts" | "answered_by" | "similar_to" | "queried_via_mcp";

export interface EdgeDecay {
  half_life_days: number;  // >= 1
  min_weight: number;      // 0–1
}

export interface EdgeTraversal {
  count: number;
  rating_avg: number | null;  // 1–5, null if no ratings
  rating_count: number;
}

export interface Edge {
  id: string;
  from_id: string;         // Memory Node ID
  to_id: string;           // Memory Node ID
  relation: RelationType;
  weight: number;          // 0–1
  co_access_count: number;
  last_co_accessed: string; // ISO 8601
  decay: EdgeDecay;
  traversal: EdgeTraversal;
}

// ─── Default factory helpers ─────────────────────────────────────────────────

export const DEFAULT_TRAVERSAL_NODE: MemoryNodeTraversal = {
  count: 0,
  unique_traversers: 0,
};

export const DEFAULT_TRAVERSAL_EDGE: EdgeTraversal = {
  count: 0,
  rating_avg: null,
  rating_count: 0,
};

export const DEFAULT_DECAY: EdgeDecay = {
  half_life_days: 30,
  min_weight: 0.1,
};

