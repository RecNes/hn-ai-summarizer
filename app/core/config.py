"""Uygulama yapılandırma ayarları."""

import os
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

    # Legacy
    LOCAL_AI_BROKER: Optional[str] = Field("")
    LOCAL_AI_BROKER_URL: Optional[str] = Field("")
    LOCAL_AI_MODEL: Optional[str] = Field("")

    DEVELOPMENT: bool = Field(False)

    @computed_field(alias="ASYNC_DATABASE_URL")
    @property
    def async_database_url(self) -> str:
        # .env'de PostgreSQL bilgileri varsa onu kullan, yoksa SQLite'a düş
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

    ASYNC_DATABASE_URL = async_database_url

    @computed_field(alias="SYNC_DATABASE_URL")
    @property
    def sync_database_url(self) -> str:
        # .env'de PostgreSQL bilgileri varsa onu kullan, yoksa SQLite'a düş
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

    SYNC_DATABASE_URL = sync_database_url

    @computed_field(alias="REDIS_CONNECTION_URL")
    @property
    def redis_connection_url(self) -> str:
        # REDIS_USERNAME ve REDIS_PASSWORD varsa URL'e ekle
        if self.REDIS_USERNAME and self.REDIS_PASSWORD:
            auth = f"{self.REDIS_USERNAME}:{self.REDIS_PASSWORD}@"
        elif self.REDIS_PASSWORD:
            auth = f":{self.REDIS_PASSWORD}@"
        else:
            auth = ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    REDIS_CONNECTION_URL = redis_connection_url

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
    )


settings = Settings()
