import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_TYPE = os.getenv("ENV", "dev")
ROOT_ENV = Path(__file__).resolve().parent.parent.parent.parent / f".env.{ENV_TYPE}"
load_dotenv(ROOT_ENV, override=False)


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    IP: str = "localhost"

    @property
    def DATABASE_URL(self):
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.IP}:5432/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()
