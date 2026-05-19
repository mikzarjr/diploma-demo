import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_TYPE = os.getenv("ENV", "dev")

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR.parent.parent.parent / f".env.{ENV_TYPE}")
load_dotenv(BASE_DIR.parent / f".env.{ENV_TYPE}")
load_dotenv(BASE_DIR / f".env.{ENV_TYPE}.backend")


class Settings(BaseSettings):
    S3_BUCKET_NAME: str = "calls-audio"
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    IP: str

    DIARIZATION_MODEL_DIR: str
    SENTIMENT_MODEL_DIR: str
    HF_TOKEN: str
    ASR_SERVICE_URL: str = "http://asr:7002"

    YANDEX_GPT_API_KEY: str
    YANDEX_GPT_FOLDER_ID: str
    YANDEX_GPT_MODEL: str = "yandexgpt/latest"
    YANDEX_GPT_URL: str = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    # CORS — exact frontend origin. JWT lives in infra/auth, not here.
    FRONTEND_ORIGIN: str

    REDIS_HOST: str
    REDIS_PORT: int = 6379
    CELERY_BROKER_DB: int = 0
    CELERY_RESULT_DB: int = 1

    TELEPHONY_WEBHOOK_SECRET: str
    PUBLIC_BASE_URL: str
    VATS_CRM_TOKEN: str
    TELEPHONY_MAX_AUDIO_MB: int

    @property
    def CELERY_BROKER_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.CELERY_BROKER_DB}"

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.CELERY_RESULT_DB}"

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()
