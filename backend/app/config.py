from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # No default — app refuses to start if DATABASE_URL is not set.
    # For local dev, set it in backend/.env
    database_url: str
    anthropic_api_key: str = ""

    # Shared secret for X-API-Key header auth. Empty = auth disabled (local dev only).
    # Production: set API_KEY to the output of `openssl rand -hex 32`
    api_key: str = ""

    # Comma-separated list of allowed CORS origins.
    # Production: set to your Railway frontend URL, e.g. https://careeros-frontend.up.railway.app
    allowed_origins: str = "http://localhost:3000"

    model_config = {"env_file": ".env"}

    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
