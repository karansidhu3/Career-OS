-- Migration 007: Add job.compression_attempts.
-- This column has existed on the SQLAlchemy model (app/models/job.py) for a
-- while, but no migration ever added it — it only ever got created via
-- Base.metadata.create_all() on databases that didn't have a job table yet.
-- Any database whose job table predates this column never received it.

ALTER TABLE job ADD COLUMN IF NOT EXISTS compression_attempts INTEGER;
