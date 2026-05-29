-- Migration 001: Add strategic_note column to job table
-- Run once on existing databases. Safe to run multiple times (IF NOT EXISTS).
-- This column is nullable — no data backfill required.

ALTER TABLE job ADD COLUMN IF NOT EXISTS strategic_note TEXT;
