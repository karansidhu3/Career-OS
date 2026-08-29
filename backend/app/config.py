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

    # ARQ job queue backend. app.main embeds the ARQ worker in the API process;
    # Redis supplies the durable queue boundary while lifecycle guards make
    # interrupted attempts visible and retryable. Local dev uses a dedicated
    # Redis instance; port 6380 avoids colliding with unrelated local projects.
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

    # Resend (Phase 6) — transactional email ONLY, scoped to one trigger: account
    # deletion confirmation. See CLAUDE.md's "What NOT to build" carve-out.
    # get_email_client() falls back to a no-op (logs, doesn't send) when unset, so local
    # dev never needs a real key.
    resend_api_key: str = ""
    email_from_address: str = "CareerOS <onboarding@resend.dev>"
    # Used to build the "sign in to download" link in the two transactional emails above.
    # Left unset in local dev — the email templates just omit the link when empty.
    frontend_url: str = ""

    # Sentry (Phase 7) — exception tracking. app.services.error_tracking.init_error_tracking()
    # is a no-op when unset, so local dev never needs a DSN or talks to Sentry at all.
    sentry_dsn: str = ""

    # Per-user daily generation cap (Phase 7) — protects a user whose leaked API key is
    # being drained through CareerOS, and protects this app's own infra from runaway
    # load. Counted over a rolling 24h window in Redis (app.routers.jobs), not calendar
    # day, so it can't be trivially reset by waiting for midnight UTC.
    daily_generation_limit: int = 20

    # Anomaly detection (Phase 7) — plain request counting, no AI. If a user crosses
    # this many generations within a 10-minute rolling window, it's logged as a
    # structured warning (e.g. for a leaked API key being drained rapidly) but not
    # blocked — daily_generation_limit above is the actual hard limit.
    velocity_anomaly_threshold: int = 5

    model_config = {"env_file": ".env"}

    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
