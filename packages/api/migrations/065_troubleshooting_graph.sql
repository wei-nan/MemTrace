-- 065_troubleshooting_graph.sql
-- Phase 6.3: Troubleshooting graph support
--
-- 1. Add metadata JSONB column to edges (needed for condition-based traversal)
-- 2. Add proceeds_to relation type (conditional next-step semantic)

-- Edge metadata (already used in code by write_mcp_interaction_edge, formalised here)
ALTER TABLE edges ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- New relation type for troubleshooting graph step-flow
ALTER TYPE relation_type ADD VALUE IF NOT EXISTS 'proceeds_to';
