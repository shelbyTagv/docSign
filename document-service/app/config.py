"""document-service/app/config.py"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DB_HOST: str = "mysql"
    DB_PORT: int = 3306
    DB_NAME: str = "docsign"
    DB_USER: str = "docsign"
    DB_PASSWORD: str
    INTERNAL_API_KEY: str
    AUTH_SERVICE_URL: str = "http://auth-service:8001"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8003"
    CORS_ORIGINS: str = "http://localhost:3000"
    FRONTEND_URL: str = "http://localhost:3000"
    PDF_STORAGE_PATH: str = "/app/storage/pdfs"
    ORG_NAME: str = "My Organization"
    ORG_TAGLINE: str = "Digital Document Management System"

    @property
    def database_url(self) -> str:
        db_type = getattr(self, 'DB_TYPE', 'postgresql')
        
        if db_type == 'mysql':
            return (
                f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
            )
        else:  # PostgreSQL default
            return (
                f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
