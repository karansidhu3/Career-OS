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

    anthropic_api_key: str = ""

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

    model_config = {"env_file": ".env"}

    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
