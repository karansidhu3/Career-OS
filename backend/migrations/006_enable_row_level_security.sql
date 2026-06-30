-- Migration 006: Row-Level Security as a defense-in-depth layer beneath the
-- application-level user_id filtering already enforced in every router.
--
-- Each table's policy requires user_id to match the session GUC
-- app.current_user_id. That GUC is set per-request in app.clerk_auth.get_current_user
-- (session-scoped via set_config(..., false) so it survives mid-request commits)
-- and reset on every request's teardown in app.database.get_db. The background
-- generation task in app.routers.jobs._run_generation sets it explicitly too,
-- since it opens its own session outside the request/dependency cycle.
--
-- current_setting(..., true) returns NULL rather than erroring when the GUC is
-- unset — and user_id = NULL is never true in SQL, so the policy fails closed:
-- no GUC set means no rows visible, not "everything visible."
--
-- FORCE is required on every table: Postgres exempts the table OWNER from RLS
-- by default, and the app's migration role is that owner (it ran
-- Base.metadata.create_all). Without FORCE, ENABLE ROW LEVEL SECURITY alone
-- would be enforced against nobody — the owner always bypasses it.
--
-- FORCE alone is still not enough. Superusers and roles with BYPASSRLS bypass
-- RLS unconditionally — no override exists, FORCE or not. The role created by
-- Postgres' POSTGRES_USER (local Docker) and most managed providers' default
-- connection role (Railway included) are superusers. The app MUST run its
-- request-handling queries through a separate, restricted role for any of this
-- to do anything. See app.config.Settings.app_database_url and
-- app.database.app_engine — request sessions use that engine, not the one
-- this migration file itself runs through.
--
-- One-time manual setup (run once per database, not part of this migration
-- file since it requires a real password — never commit one to a SQL file):
--
--   CREATE ROLE careeros_app WITH LOGIN PASSWORD '<generate with: openssl rand -hex 24>'
--       NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
--   GRANT CONNECT ON DATABASE <dbname> TO careeros_app;
--   GRANT USAGE ON SCHEMA public TO careeros_app;
--   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO careeros_app;
--   GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO careeros_app;
--   ALTER DEFAULT PRIVILEGES FOR ROLE <owner-role> IN SCHEMA public
--       GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO careeros_app;
--   ALTER DEFAULT PRIVILEGES FOR ROLE <owner-role> IN SCHEMA public
--       GRANT USAGE, SELECT ON SEQUENCES TO careeros_app;
--
-- Then set APP_DATABASE_URL to a connection string using careeros_app's
-- credentials. DATABASE_URL keeps pointing at the original owner role —
-- migrations and Base.metadata.create_all still need that role's privileges.

ALTER TABLE job            ENABLE ROW LEVEL SECURITY;
ALTER TABLE personal_info  ENABLE ROW LEVEL SECURITY;
ALTER TABLE education      ENABLE ROW LEVEL SECURITY;
ALTER TABLE experience     ENABLE ROW LEVEL SECURITY;
ALTER TABLE project        ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_category ENABLE ROW LEVEL SECURITY;

ALTER TABLE job            FORCE ROW LEVEL SECURITY;
ALTER TABLE personal_info  FORCE ROW LEVEL SECURITY;
ALTER TABLE education      FORCE ROW LEVEL SECURITY;
ALTER TABLE experience     FORCE ROW LEVEL SECURITY;
ALTER TABLE project        FORCE ROW LEVEL SECURITY;
ALTER TABLE skill_category FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON job;
CREATE POLICY tenant_isolation ON job
    USING (user_id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON personal_info;
CREATE POLICY tenant_isolation ON personal_info
    USING (user_id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON education;
CREATE POLICY tenant_isolation ON education
    USING (user_id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON experience;
CREATE POLICY tenant_isolation ON experience
    USING (user_id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON project;
CREATE POLICY tenant_isolation ON project
    USING (user_id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON skill_category;
CREATE POLICY tenant_isolation ON skill_category
    USING (user_id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);
