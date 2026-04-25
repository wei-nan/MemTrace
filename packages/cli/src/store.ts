/**
 * Local file-system store for Phase 1 (CLI).
 * All data lives under ~/.memtrace/
 */
import fs   from "fs";
import path from "path";
import os   from "os";
import type { MemoryNode, Edge } from "@memtrace/core";

export const MEMTRACE_DIR  = path.join(os.homedir(), ".memtrace");
export const CONFIG_FILE   = path.join(MEMTRACE_DIR, "config.json");
export const NODES_DIR     = path.join(MEMTRACE_DIR, "nodes");
export const EDGES_DIR     = path.join(MEMTRACE_DIR, "edges");

export function ensureDirs(): void {
  [MEMTRACE_DIR, NODES_DIR, EDGES_DIR].forEach(d => {
    if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true });
  });
}

// ─── Config ──────────────────────────────────────────────────────────────────

export interface Config {
  auth?: { token: string };
  api_url?: string;
  default_workspace?: string;
  ai?: {
    provider: "openai" | "anthropic";
    api_keys: Partial<Record<"openai" | "anthropic", string>>;
  };
}

export function readConfig(): Config {
  if (!fs.existsSync(CONFIG_FILE)) return {};
  try {
    return JSON.parse(fs.readFileSync(CONFIG_FILE, "utf8"));
  } catch {
    return {};
  }
}

export function writeConfig(cfg: Config): void {
  ensureDirs();
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(cfg, null, 2), { mode: 0o600 });
}

// ─── Nodes ───────────────────────────────────────────────────────────────────

export function saveNode(node: MemoryNode): void {
  ensureDirs();
  fs.writeFileSync(
    path.join(NODES_DIR, `${node.id}.json`),
    JSON.stringify(node, null, 2)
  );
}

export function loadNode(id: string): MemoryNode | null {
  const file = path.join(NODES_DIR, `${id}.json`);
  if (!fs.existsSync(file)) return null;
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

export function listNodes(): MemoryNode[] {
  if (!fs.existsSync(NODES_DIR)) return [];
  return fs.readdirSync(NODES_DIR)
    .filter(f => f.endsWith(".json"))
    .map(f => JSON.parse(fs.readFileSync(path.join(NODES_DIR, f), "utf8")));
}

export function deleteNode(id: string): boolean {
  const file = path.join(NODES_DIR, `${id}.json`);
  if (!fs.existsSync(file)) return false;
  fs.unlinkSync(file);
  return true;
}

// ─── Edges ───────────────────────────────────────────────────────────────────

export function saveEdge(edge: Edge): void {
  ensureDirs();
  fs.writeFileSync(
    path.join(EDGES_DIR, `${edge.id}.json`),
    JSON.stringify(edge, null, 2)
  );
}

export function listEdges(): Edge[] {
  if (!fs.existsSync(EDGES_DIR)) return [];
  return fs.readdirSync(EDGES_DIR)
    .filter(f => f.endsWith(".json"))
    .map(f => JSON.parse(fs.readFileSync(path.join(EDGES_DIR, f), "utf8")));
}
