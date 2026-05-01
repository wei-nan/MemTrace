-- Migration: Add fields for PDF metadata
-- Phase 4.3: A-1

ALTER TABLE import_sources ADD COLUMN IF NOT EXISTS page_count INTEGER;
ALTER TABLE import_sources ADD COLUMN IF NOT EXISTS has_ocr BOOLEAN DEFAULT FALSE;
