from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    app_secret_key: SecretStr
    postgres_user: str = "qa_portal"
    postgres_password: SecretStr
    postgres_db: str = "qa_portal"
    postgres_host: str = "db"
    allowed_origins: str = "http://localhost:8080,http://127.0.0.1:8080"
    cookie_secure: bool = False  # Loopback HTTP only; enable when serving HTTPS.
    slack_webhook_url: SecretStr = SecretStr("")
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: str = ""

    @field_validator("app_secret_key")
    @classmethod
    def strong_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("APP_SECRET_KEY must contain at least 32 characters")
        return value

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # pydantic-settings supplies environment values.
