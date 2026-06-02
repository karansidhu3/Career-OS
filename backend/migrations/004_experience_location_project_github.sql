-- Migration 004: Add location to experience, github_url to project
-- Both columns are optional (nullable TEXT).

ALTER TABLE experience ADD COLUMN IF NOT EXISTS location TEXT;
ALTER TABLE project    ADD COLUMN IF NOT EXISTS github_url TEXT;
