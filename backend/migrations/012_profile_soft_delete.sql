-- Migration 012: Soft-delete + undo on profile sections (Phase 6).
-- NULL deleted_at means active. Existing rows are unaffected (NULL by default).

ALTER TABLE education      ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE experience     ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE project        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE skill_category ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
