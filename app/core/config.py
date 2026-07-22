"""Uygulama yapılandırma ayarları."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field

# Force-load .env into environment before Pydantic reads it
from dotenv import load_dotenv

load_dotenv(".env")


class Settings(BaseSettings):
    """Uygulama yapılandırma ayarları."""

    PROJECT_NAME: str = "HN-AI-Summerizer"
    PROJECT_VERSION: str = "0.1.0"
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
    REDIS_USERNAME: Optional[str] = Field("")
    REDIS_PASSWORD: Optional[str] = Field("")

    # AI Provider API Keys (only read from .env, never exposed to frontend)
    OPENAI_API_KEY: Optional[str] = Field("")
    ANTHROPIC_API_KEY: Optional[str] = Field("")
    DEEPSEEK_API_KEY: Optional[str] = Field("")
    OPENROUTER_API_KEY: Optional[str] = Field("")
    GEMINI_API_KEY: Optional[str] = Field("")

    # Legacy
    LOCAL_AI_BROKER: Optional[str] = Field("")
    LOCAL_AI_BROKER_URL: Optional[str] = Field("")
    LOCAL_AI_MODEL: Optional[str] = Field("")

    TELEGRAM_BOT_TOKEN: Optional[str] = Field("")

    # Public URL for links in notifications (Telegram, email, etc.)
    # Example: https://hnreader.example.com
    PUBLIC_URL: Optional[str] = Field("http://localhost:8000")

    DEVELOPMENT: bool = Field(False)

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