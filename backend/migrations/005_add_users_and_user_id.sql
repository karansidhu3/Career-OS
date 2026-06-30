-- Migration 005: Multi-tenant foundation.
-- Adds the users table (Clerk-backed identity) and a nullable user_id FK on
-- every table that previously had no ownership concept. Nullable for now —
-- existing rows are claimed by the first JIT-provisioned user at app startup
-- (see app/services/auth_provisioning.py), then a later migration tightens
-- these columns to NOT NULL once that claim is verified.

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_user_id TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE job           ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
ALTER TABLE personal_info ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
ALTER TABLE education     ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
ALTER TABLE experience    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
ALTER TABLE project       ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
ALTER TABLE skill_category ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);

CREATE INDEX IF NOT EXISTS idx_job_user_id ON job(user_id);
CREATE INDEX IF NOT EXISTS idx_personal_info_user_id ON personal_info(user_id);
CREATE INDEX IF NOT EXISTS idx_education_user_id ON education(user_id);
CREATE INDEX IF NOT EXISTS idx_experience_user_id ON experience(user_id);
CREATE INDEX IF NOT EXISTS idx_project_user_id ON project(user_id);
CREATE INDEX IF NOT EXISTS idx_skill_category_user_id ON skill_category(user_id);
