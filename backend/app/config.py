from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/careeros"
    anthropic_api_key: str = ""
    # Comma-separated list of allowed CORS origins.
    # In production: set to the Railway frontend URL, e.g. https://careeros.up.railway.app
    allowed_origins: str = "http://localhost:3000"

    model_config = {"env_file": ".env"}

    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
