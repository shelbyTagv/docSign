"""
auth-service/app/config.py

Centralised settings loaded from environment variables via pydantic-settings.
A single Settings instance is instantiated at module level — all other modules
import `settings` from here. This avoids scattered os.getenv() calls and gives
us type-validated, documented configuration.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ─── Database ─────────────────────────────────────────────
    DB_HOST: str = "mysql"
    DB_PORT: int = 3306
    DB_NAME: str = "docsign"
    DB_USER: str = "docsign"
    DB_PASSWORD: str

    # ─── JWT ──────────────────────────────────────────────────
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── Encryption ───────────────────────────────────────────
    MASTER_ENCRYPTION_KEY: str  # Fernet key for MFA secrets and signatures

    # ─── Inter-service Auth ───────────────────────────────────
    INTERNAL_API_KEY: str  # Shared secret for service-to-service calls

    # ─── CORS ─────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000"

    # ─── Application ──────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"
    ORG_NAME: str = "My Organization"

    # ─── Notification Service ─────────────────────────────────
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8003"

    @property
    def database_url(self) -> str:
        """Construct MySQL connection URL. PyMySQL is the pure-Python driver
        that works in slim containers without system libmysqlclient."""
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore unknown env vars — other services share the same .env


@lru_cache()
def get_settings() -> Settings:
    """Cached settings factory — reads .env exactly once."""
    return Settings()


settings = get_settings()
