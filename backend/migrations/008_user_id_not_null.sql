-- Migration 008: Tighten user_id to NOT NULL now that the legacy-data claim
-- (app.clerk_auth._claim_legacy_data, triggered once by the first real sign-in)
-- has run and every pre-existing row is owned. Every row created from here on
-- is always written with a user_id by the application — these columns being
-- nullable was only ever a transitional state for the migration 005 backfill.
--
-- Safe to run unconditionally: ALTER COLUMN ... SET NOT NULL fails loudly if
-- any row still has a NULL user_id, rather than silently succeeding — so this
-- can't accidentally lock out legitimate unclaimed data.

ALTER TABLE job            ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE personal_info  ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE education      ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE experience     ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE project        ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE skill_category ALTER COLUMN user_id SET NOT NULL;
