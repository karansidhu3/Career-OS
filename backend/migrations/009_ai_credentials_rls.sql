-- Migration 009: Row-Level Security on ai_credentials (Phase 3 — BYO API keys).
-- The table itself is created by Base.metadata.create_all (app.models.ai_credential);
-- this migration only adds the same tenant_isolation policy pattern as migration 006.
-- Encrypted key material never leaves the DB decrypted except in-process when a
-- generation call needs it — RLS is still defense-in-depth, same rationale as 006.

ALTER TABLE ai_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_credentials FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON ai_credentials;
CREATE POLICY tenant_isolation ON ai_credentials
    USING (user_id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);
