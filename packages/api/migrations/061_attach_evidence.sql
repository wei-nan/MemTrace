-- Migration 061: evidence_type for documents (C1-T25)

BEGIN;

ALTER TABLE documents 
  ADD COLUMN evidence_type TEXT NOT NULL DEFAULT 'human_upload'
  CHECK (evidence_type IN ('human_upload', 'agent_attached'));

COMMIT;
