-- Migration: 059_gap_content_type.sql
-- Add 'gap' value to content_type enum for knowledge gaps

ALTER TYPE content_type ADD VALUE IF NOT EXISTS 'gap';
