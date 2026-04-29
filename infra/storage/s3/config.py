import os
from pathlib import Path

import boto3
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_TYPE = os.getenv("ENV", "dev")
ROOT_ENV = Path(__file__).resolve().parent.parent.parent.parent / f".env.{ENV_TYPE}"
load_dotenv(ROOT_ENV, override=False)


class Settings(BaseSettings):
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    IP: str = "localhost"
    S3_BUCKET_NAME: str = "calls-audio"
    S3_ENDPOINT_URL: str | None = None

    @property
    def S3_URL(self):
        if self.S3_ENDPOINT_URL:
            return self.S3_ENDPOINT_URL
        return f"http://{self.IP}:9000"

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_URL,
        aws_access_key_id=settings.MINIO_ROOT_USER,
        aws_secret_access_key=settings.MINIO_ROOT_PASSWORD,
    )
