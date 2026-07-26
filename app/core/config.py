"""Uygulama yapılandırma ayarları."""


# Force-load .env into environment before Pydantic reads it
from dotenv import load_dotenv
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(".env")


class Settings(BaseSettings):
    """Uygulama yapılandırma ayarları."""

    PROJECT_NAME: str = "HN-AI-Summerizer"
    PROJECT_VERSION: str = Field(default="0.0.0", validation_alias="APP_VERSION")
    PROJECT_DESCRIPTION: str = "AI-powered Hacker News summarizer"

    DATABASE_USER: str = Field(default="postgres")
    DATABASE_PASSWORD: str = Field(default="postgres")
    DATABASE_HOST: str = Field(default="localhost")
    DATABASE_PORT: str = Field(default="5432")
    DATABASE_NAME: str = Field(default="hn_ai_summerizer_db")

    DB_ECHO: bool = Field(False)

    REDIS_HOST: str = Field("localhost")
    REDIS_PORT: int = Field(6379)
    REDIS_DB: int = Field(0)
    REDIS_USERNAME: str | None = Field("")
    REDIS_PASSWORD: str | None = Field("")

    # AI Provider API Keys (only read from .env, never exposed to frontend)
    OPENAI_API_KEY: str | None = Field("")
    ANTHROPIC_API_KEY: str | None = Field("")
    DEEPSEEK_API_KEY: str | None = Field("")
    OPENROUTER_API_KEY: str | None = Field("")
    GEMINI_API_KEY: str | None = Field("")

    # Legacy
    LOCAL_AI_BROKER: str | None = Field("")
    LOCAL_AI_BROKER_URL: str | None = Field("")
    LOCAL_AI_MODEL: str | None = Field("")

    TELEGRAM_BOT_TOKEN: str | None = Field("")

    # Public URL for links in notifications (Telegram, email, etc.)
    # Example: https://hnreader.example.com
    PUBLIC_URL: str | None = Field("http://localhost:8000")

    DEVELOPMENT: bool = Field(False)

    # Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    LOG_LEVEL: str = Field("INFO")

    # Delay in seconds between HN API requests (throttle)
    HN_REQUEST_DELAY: float = Field(0.5)

    # Interval in seconds to wait before retrying failed fetch/process
    AI_RETRY_INTERVAL: int = Field(300)

    @computed_field
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        if self.DATABASE_HOST and self.DATABASE_HOST not in ("localhost", "db"):
            return (
                f"postgresql+asyncpg://{self.DATABASE_USER}:"
                f"{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:"
                f"{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            )
        if not self.DEVELOPMENT:
            return (
                f"postgresql+asyncpg://{self.DATABASE_USER}:"
                f"{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:"
                f"{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            )
        return "sqlite+aiosqlite:///./hn_ai_summerizer.db"

    @computed_field
    @property
    def SYNC_DATABASE_URL(self) -> str:
        if self.DATABASE_HOST and self.DATABASE_HOST not in ("localhost", "db"):
            return (
                f"postgresql://{self.DATABASE_USER}:"
                f"{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}"
                f":{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            )
        if not self.DEVELOPMENT:
            return (
                f"postgresql://{self.DATABASE_USER}:"
                f"{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}"
                f":{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            )
        return "sqlite:///./hn_ai_summerizer.db"

    @computed_field
    @property
    def REDIS_CONNECTION_URL(self) -> str:
        if self.REDIS_USERNAME and self.REDIS_PASSWORD:
            auth = f"{self.REDIS_USERNAME}:{self.REDIS_PASSWORD}@"
        elif self.REDIS_PASSWORD:
            auth = f":{self.REDIS_PASSWORD}@"
        else:
            auth = ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
    )


settings = Settings() # type: ignore