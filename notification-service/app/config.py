"""notification-service/app/config.py"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = "DocSign Platform <noreply@docsign.local>"
    INTERNAL_API_KEY: str = "change-me"
    FRONTEND_URL: str = "http://localhost:3000"
    ORG_NAME: str = "My Organization"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
