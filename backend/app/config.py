from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/careeros"
    anthropic_api_key: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
