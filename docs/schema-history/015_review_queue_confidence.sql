SET client_encoding = 'UTF8';
-- C5: AI Review confidence score
ALTER TABLE review_queue ADD COLUMN IF NOT EXISTS confidence_score FLOAT DEFAULT NULL;
