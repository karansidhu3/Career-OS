from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # No default — app refuses to start if DATABASE_URL is not set.
    # For local dev, set it in backend/.env. Elevated-privilege role — owns the
    # schema, runs migrations. Never used for request handling (see app_database_url).
    database_url: str

    # Restricted, non-superuser role every request actually queries through.
    # Required for Row-Level Security (migration 006) to mean anything — Postgres
    # exempts superusers and BYPASSRLS roles from RLS unconditionally, FORCE or not.
    # Falls back to database_url when unset (RLS is then a no-op, not an error).
    app_database_url: str = ""

    # Envelope-encryption key for per-user AI provider credentials (Phase 3).
    # Must be a Fernet key (generate with `Fernet.generate_key()`), stored as a
    # Railway secret — never in code or the database. Rotation: move the old
    # key into encryption_master_key_previous (comma-separated if more than
    # one) when rotating so already-encrypted rows keep decrypting.
    encryption_master_key: str = ""
    encryption_master_key_previous: str = ""

    # Set DEV_MODE=true in local .env to allow running without Clerk configured.
    # Never set this in production — the startup check enforces it.
    dev_mode: bool = False

    # Comma-separated list of allowed CORS origins.
    # Production: set to your Railway frontend URL, e.g. https://careeros-frontend.up.railway.app
    allowed_origins: str = "http://localhost:3000"

    # Clerk dashboard → API Keys. Secret key calls the Clerk Backend API (JIT user email lookup).
    # Frontend API domain is the host Clerk session JWTs are issued from — used to build the JWKS URL.
    clerk_secret_key: str = ""
    clerk_frontend_api_domain: str = ""

    # ARQ job queue backend (Phase 5). Generation runs in a separate worker process
    # (`arq app.worker.WorkerSettings`) so a redeploy/crash of the API doesn't lose
    # in-flight jobs the way in-process BackgroundTasks did. Local dev: a dedicated
    # `careeros-redis` Docker container, not the default 6379 port (see backend
    # README/CLAUDE notes — 6379 is often occupied by an unrelated project locally).
    redis_url: str = "redis://localhost:6380"

    # Local-filesystem PDF cache (Phase 5). Compiled once at generation time instead
    # of recompiling LaTeX on every download. Used when R2 isn't configured (local
    # dev, or before R2_BUCKET_NAME etc. are set) — see app.services.pdf_storage.
    pdf_storage_dir: str = "./pdf_storage"

    # Cloudflare R2 (S3-compatible) PDF storage — the production backend for the
    # same cache. get_pdf_storage() picks R2 automatically once r2_bucket_name is
    # set; leaving it unset keeps using the local-filesystem fallback above.
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""

    model_config = {"env_file": ".env"}

    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
