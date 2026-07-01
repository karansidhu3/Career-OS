-- Migration 010: Row-Level Security on account_exports (Phase 6 — data export).
-- The table itself is created by Base.metadata.create_all (app.models.account_export);
-- this migration only adds the same tenant_isolation policy pattern as migrations 006/009.

ALTER TABLE account_exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE account_exports FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON account_exports;
CREATE POLICY tenant_isolation ON account_exports
    USING (user_id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);
