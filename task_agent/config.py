from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env lives at the repo root (TheGlucoGardener/.env)
_ENV_FILE = Path(__file__).parent / ".env"

class Settings(BaseSettings):
    sea_lion_api_key: str = "dummy_key"
    google_maps_api_key: str = "dummy_key"
    gemini_api_key: str = "dummy_key"
    database_url: str = "sqlite:///./task_agent.db"
    redis_url: str = "redis://localhost:6379/0"

    pg_host: str = ""
    pg_port: int = 5432
    pg_user: str = ""
    pg_password: str = ""
    pg_db: str = ""

    @model_validator(mode="after")
    def build_database_url_from_pg_vars(self) -> "Settings":
        if self.pg_host and self.pg_user and self.pg_db:
            self.database_url = (
                f"postgresql+psycopg2://{self.pg_user}:{self.pg_password}"
                f"@{self.pg_host}:{self.pg_port}/{self.pg_db}"
            )
        return self

    @property
    def async_database_url(self) -> str:
        return self.database_url.replace(
            "postgresql+psycopg2://", "postgresql+asyncpg://"
        ).replace(
            "sqlite:///", "sqlite+aiosqlite:///"
        )

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
