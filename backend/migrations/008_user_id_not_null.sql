-- Migration 008: Tighten user_id to NOT NULL once the legacy-data claim
-- (app.clerk_auth._claim_legacy_data, triggered once by the first real sign-in)
-- has run and every pre-existing row is owned. Every row created from here on
-- is always written with a user_id by the application — these columns being
-- nullable was only ever a transitional state for the migration 005 backfill.
--
-- Guarded, not unconditional: this file runs automatically on every startup
-- (app.main._run_migrations), before anyone has necessarily signed in yet.
-- On a fresh deploy, the legacy claim hasn't fired — rows still have NULL
-- user_id — and an unconditional ALTER COLUMN ... SET NOT NULL would raise
-- and crash startup entirely (this happened: NotNullViolationError on
-- production before this fix). Each block below only tightens the constraint
-- once zero NULL rows remain, so it's a no-op until the claim has actually
-- run, and self-applies on a later restart once it has.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM job WHERE user_id IS NULL) THEN
    ALTER TABLE job ALTER COLUMN user_id SET NOT NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM personal_info WHERE user_id IS NULL) THEN
    ALTER TABLE personal_info ALTER COLUMN user_id SET NOT NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM education WHERE user_id IS NULL) THEN
    ALTER TABLE education ALTER COLUMN user_id SET NOT NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM experience WHERE user_id IS NULL) THEN
    ALTER TABLE experience ALTER COLUMN user_id SET NOT NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM project WHERE user_id IS NULL) THEN
    ALTER TABLE project ALTER COLUMN user_id SET NOT NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM skill_category WHERE user_id IS NULL) THEN
    ALTER TABLE skill_category ALTER COLUMN user_id SET NOT NULL;
  END IF;
END $$;
