# Template Knowledge Base: Spec-as-KB

This document serves as a reference for the **Spec-as-KB** template knowledge base located at `examples/spec-as-kb`. 

## Overview
The Spec-as-KB is a demonstration of MemTrace's core philosophy: **"One idea per node, value through connections."** It represents the MemTrace project specification itself as a MemTrace knowledge base.

- **Storage Path**: `file:///d:/Workspace/MemTrace/examples/spec-as-kb`
- **Total Nodes**: 19 Memory Nodes
- **Total Edges**: 37 Edges

## Core Clusters
The KB is organized into 7 clusters:

1. **Philosophy (P)**: Core product concepts.
   - `mem_p001`: 知識透過連結而非積累
   - `mem_p002`: 為知識傳承而設計
2. **Data Model (D)**: Schema definitions.
   - `mem_d001`: Memory Node structure
   - `mem_d005`: Provenance (Source tracking)
3. **Graph Mechanics (G)**: How the graph behaves.
   - `mem_g001`: Decay mechanism
   - `mem_g003`: Edge relationship types
4. **Knowledge Base (K)**: Workspace management.
   - `mem_k001`: Knowledge Base (Workspace) definition
5. **AI Features (A)**: Extraction and review.
   - `mem_a002`: AI-driven node extraction from documents
6. **Integration (I)**: Auth and External APIs.
   - `mem_i003`: MCP Server (AI Agent integration)
7. **Onboarding (O)**: User entry points.
   - `mem_o001`: Web UI Wizard

## Relationship Types
The template uses four primary relationship types (as defined in `mem_g003`):
- `extends`: Specialization or refinement.
- `depends_on`: Foundational requirement.
- `related_to`: Weak semantic link.
- `references`: Citation or external source.

## Usage for Reference
This template can be used as a:
1. **Schema Reference**: Check `nodes/*.json` for real-world application of `node.v1.json`.
2. **Logical Blueprint**: Understand how feature requirements (e.g., AI Extraction) connect to data models (Memory Nodes).
3. **Seeding Template**: Use this structure to initialize new knowledge bases.

---
*For the full graph visualization and node details, refer to [examples/spec-as-kb/README.md](file:///d:/Workspace/MemTrace/examples/spec-as-kb/README.md).*
