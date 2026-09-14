-- Local-only role setup. The app connects as this non-superuser role for request
-- handling, so the same Row-Level Security path is exercised during local work.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'careeros_app') THEN
    CREATE ROLE careeros_app LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
  END IF;
END
$$;

GRANT CONNECT ON DATABASE careeros TO careeros_app;
GRANT USAGE ON SCHEMA public TO careeros_app;
ALTER DEFAULT PRIVILEGES FOR ROLE careeros IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO careeros_app;
ALTER DEFAULT PRIVILEGES FOR ROLE careeros IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO careeros_app;
