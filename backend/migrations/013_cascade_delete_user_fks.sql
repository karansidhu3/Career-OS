-- Migration 013: ON DELETE CASCADE on every user_id foreign key (security
-- audit hardening). app.services.account_deletion.hard_delete_user() already
-- deletes every user-scoped row in the correct order inside one transaction —
-- this is defense-in-depth, not a behavior change, for the case where a user
-- row is ever deleted through some path that isn't that function (a future
-- admin script, a manual psql session, etc.). Without this, such a delete
-- would fail outright (Postgres defaults an unspecified FK to RESTRICT) rather
-- than leaving orphans, but failing loudly on a scenario that should just work
-- isn't better than cascading correctly.
--
-- Idempotent: drop-then-recreate is safe to run on every startup, matching
-- every other migration in this directory.

ALTER TABLE personal_info DROP CONSTRAINT IF EXISTS personal_info_user_id_fkey;
ALTER TABLE personal_info ADD CONSTRAINT personal_info_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE education DROP CONSTRAINT IF EXISTS education_user_id_fkey;
ALTER TABLE education ADD CONSTRAINT education_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE experience DROP CONSTRAINT IF EXISTS experience_user_id_fkey;
ALTER TABLE experience ADD CONSTRAINT experience_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE project DROP CONSTRAINT IF EXISTS project_user_id_fkey;
ALTER TABLE project ADD CONSTRAINT project_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE skill_category DROP CONSTRAINT IF EXISTS skill_category_user_id_fkey;
ALTER TABLE skill_category ADD CONSTRAINT skill_category_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE job DROP CONSTRAINT IF EXISTS job_user_id_fkey;
ALTER TABLE job ADD CONSTRAINT job_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE ai_credentials DROP CONSTRAINT IF EXISTS ai_credentials_user_id_fkey;
ALTER TABLE ai_credentials ADD CONSTRAINT ai_credentials_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- account_exports was dropped in migration 016 (ADR-017) — guarded the same
-- way as migration 010, since this file replays on every startup too.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'account_exports') THEN
        ALTER TABLE account_exports DROP CONSTRAINT IF EXISTS account_exports_user_id_fkey;
        ALTER TABLE account_exports ADD CONSTRAINT account_exports_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    END IF;
END $$;
