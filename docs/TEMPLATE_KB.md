# Template Knowledge Base: Spec-as-KB

This document is a reference for the **Spec-as-KB** template located at `examples/spec-as-kb`.

> **Last synced:** 2026-04-27 — counts and relation types verified against the JSON files in `examples/spec-as-kb/`.

## Overview

Spec-as-KB demonstrates MemTrace's core philosophy: **"One idea per node, value through connections."** It expresses the MemTrace product specification itself as a MemTrace knowledge base.

- **Storage path**: `examples/spec-as-kb/`
- **Total nodes**: **30** Memory Nodes (one JSON file per node under `nodes/`)
- **Total edges**: **54** Edges (in `edges/edges.json`)

---

## Three things that share the name "spec-as-KB"

It is easy to confuse three related-but-different artifacts. Keep them straight:

| Artifact | What it is | Where it lives | Who reads it |
|----------|-----------|----------------|--------------|
| **`examples/spec-as-kb/`** (this template) | A static set of 30 JSON node files + 1 edges file | Repo only | Developers learning the schema |
| **`ws_spec0001`** (live KB) | A running, public workspace seeded from this template, then grown over time with AI-extracted nodes | Database, applied via `schema/sql/099_seed_spec_kb.sql` | Any logged-in user — appears in their workspace list |
| **A new user's first KB** | An **empty** workspace created during onboarding | Per-user (no preload) | The user themselves |

> A new user does **not** receive a copy of spec-as-KB on signup. They build their own KB from scratch (the onboarding wizard guides them through it). They will, however, see `ws_spec0001` in their workspace list because it is `visibility=public`. That public KB is the entry point we use to demonstrate MemTrace at conferences and onboarding sessions.

---

## Cluster overview

The 30 nodes are grouped into seven clusters by ID prefix:

| Prefix | Cluster | Node IDs |
|--------|---------|----------|
| `p` | **Philosophy** — core product concepts | `mem_p001`, `mem_p002`, `mem_p003` |
| `d` | **Data Model** — schemas & dimensions | `mem_d001` ~ `mem_d006` |
| `g` | **Graph Mechanics** — decay, edge types | `mem_g001`, `mem_g002`, `mem_g003` |
| `k` | **Knowledge Base** — workspace concepts | `mem_k001` ~ `mem_k004` |
| `a` | **AI Features** — provider, ingestion, review, Q&A | `mem_a001` ~ `mem_a004` |
| `i` | **Integration** — auth, MCP, external APIs | `mem_i001` ~ `mem_i004` |
| `o` | **Onboarding** — entry-point flows | `mem_o001`, `mem_o002` |
| `w` | **Workflow** — operational walkthroughs | `mem_w001` ~ `mem_w004` |

> 8 prefixes total (P / D / G / K / A / I / O / W). Earlier docs sometimes mentioned only the first 7 — `w` was added later as setup walkthroughs landed.

---

## Relationship types

The template uses MemTrace's four canonical edge types (defined in `mem_g003` and SPEC.md §4.2):

| Type | Meaning |
|------|---------|
| `depends_on` | This node requires the target to make sense |
| `extends` | This node specializes or refines the target |
| `related_to` | Weak semantic link, no precedence |
| `contradicts` | Logical conflict / version mismatch |

> Earlier revisions of this document mistakenly listed `references` as a fourth type — that was never in the schema. The four types above are the only valid ones.

---

## How to use this template

1. **Schema Reference** — open any file under `nodes/*.json` for a real-world example of `schema/node.v1.json`. Open `edges/edges.json` for `schema/edge.v1.json`.
2. **Logical Blueprint** — trace any node's edges to see how a feature requirement (e.g. AI extraction) connects back to its data-model foundations.
3. **Seeding Template** — `schema/sql/099_seed_spec_kb.sql` was generated from this template (with later AI-extracted additions). To bootstrap a *fresh* spec-as-KB without the historical drift, re-import directly from these JSON files.

---

*For the full graph visualisation and per-node details, see [examples/spec-as-kb/README.md](../examples/spec-as-kb/README.md).*
