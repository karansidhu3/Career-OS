-- Migration 002: Replace bullets/tech arrays with prose description fields
-- Applies to: experience, project tables
-- Safe to run multiple times (IF NOT EXISTS / IF EXISTS guards).
-- Existing bullet/tech data will be dropped — profile should be re-entered via profile editor.

ALTER TABLE experience ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT '';
ALTER TABLE project    ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT '';
ALTER TABLE experience DROP COLUMN IF EXISTS bullets;
ALTER TABLE project    DROP COLUMN IF EXISTS bullets;
ALTER TABLE project    DROP COLUMN IF EXISTS tech;
