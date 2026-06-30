from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # No default — app refuses to start if DATABASE_URL is not set.
    # For local dev, set it in backend/.env
    database_url: str
    anthropic_api_key: str = ""

    # Shared secret for X-API-Key header auth.
    # Production: set API_KEY to the output of `openssl rand -hex 32`
    # Local dev: set DEV_MODE=true in .env to bypass auth without a key
    api_key: str = ""

    # Set DEV_MODE=true in local .env to allow running without API_KEY.
    # Never set this in production — the startup check enforces it.
    dev_mode: bool = False

    # Comma-separated list of allowed CORS origins.
    # Production: set to your Railway frontend URL, e.g. https://careeros-frontend.up.railway.app
    allowed_origins: str = "http://localhost:3000"

    model_config = {"env_file": ".env"}

    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
