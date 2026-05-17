-- S3-T02: Cross-workspace version synchronization
-- 1. Add FK and Index to copied_from_node for efficient tracking
ALTER TABLE memory_nodes 
  ADD CONSTRAINT fk_memory_nodes_copied_from 
  FOREIGN KEY (copied_from_node) 
  REFERENCES memory_nodes(id) 
  ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_nodes_copied_from ON memory_nodes(copied_from_node);

-- 2. Add source_updated to allowed values if needed (change_type is TEXT, so no enum change needed)
-- 3. Add metadata to review_queue if not present (already present from 009)
