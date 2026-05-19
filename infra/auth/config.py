"""
Auth service settings.

Loads from (in order, later overrides):
1. Repo-root /.env.{ENV}            — POSTGRES_USER/PASSWORD/DB, IP, etc.
2. infra/auth/.env.{ENV}             — JWT_SECRET, expiries
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_TYPE = os.getenv("ENV", "dev")
HERE = Path(__file__).resolve().parent

load_dotenv(HERE.parent.parent / f".env.{ENV_TYPE}", override=False)
load_dotenv(HERE / f".env.{ENV_TYPE}", override=False)


class Settings(BaseSettings):
    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # DB (used via shared infra.storage.db.database which reads same vars)
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    IP: str = "localhost"

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()
