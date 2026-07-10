-- Migration 010: Row-Level Security on account_exports (Phase 6 — data export).
-- The account export feature was removed in ADR-017 (see migration 016, which
-- drops this table). Every migration replays on every startup (app.main's
-- _run_migrations, alphabetical order) — since 016 sorts after 010 and drops
-- the table for good, 010 has to tolerate the table no longer existing on any
-- startup from that point on, not just the one where 016 first runs. Guarded
-- with a DO block instead of deleting this file outright, so the historical
-- record of what Phase 6 originally set up stays intact.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'account_exports') THEN
        ALTER TABLE account_exports ENABLE ROW LEVEL SECURITY;
        ALTER TABLE account_exports FORCE ROW LEVEL SECURITY;

        DROP POLICY IF EXISTS tenant_isolation ON account_exports;
        CREATE POLICY tenant_isolation ON account_exports
            USING (user_id = current_setting('app.current_user_id', true)::uuid)
            WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);
    END IF;
END $$;
