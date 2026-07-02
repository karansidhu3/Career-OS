-- Migration 011: Add users.scheduled_deletion_at (Phase 6 — account deletion grace period).

ALTER TABLE users ADD COLUMN IF NOT EXISTS scheduled_deletion_at TIMESTAMPTZ;
