import os
import secrets
from typing import List, Set
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "EduSense AI — Automated Answer Evaluation System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/edusense_db"
    )

    # JWT Authentication & Secret Keys
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-jwt-secret-key-edusense-2026-v1-distinct")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Admin & Service Authorization Keys
    ADMIN_SECRET_KEY: str = os.getenv("ADMIN_SECRET_KEY", "dev-admin-provisioning-key-edusense-2026-v2-distinct")
    EVALUATION_SERVICE_KEY: str = os.getenv("EVALUATION_SERVICE_KEY", "dev-ai-eval-service-key-edusense-2026-v3-distinct")

    # Explicit Trusted CORS Origins (No Wildcards in Production)
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def validate_secrets(self) -> None:
        """
        Validates secret configuration:
        1. In production, raises ValueError if any secret is missing, weak, or a known placeholder.
        2. In all environments, enforces that SECRET_KEY, ADMIN_SECRET_KEY, and EVALUATION_SERVICE_KEY are distinct.
        """
        known_placeholders: Set[str] = {
            "edusense-super-secret-jwt-key-change-in-production-2026",
            "edusense-dev-jwt-secret-key-2026",
            "edusense-admin-key-2026",
            "edusense-ai-eval-service-key-2026",
            "dev-jwt-secret-key-edusense-2026-v1-distinct",
            "dev-admin-provisioning-key-edusense-2026-v2-distinct",
            "dev-ai-eval-service-key-edusense-2026-v3-distinct",
            "secret",
            "admin",
            "change-me",
            "change-in-production",
            "12345",
            "password",
            ""
        }

        # 1. Enforce distinct keys across all environments
        if (self.SECRET_KEY == self.ADMIN_SECRET_KEY or
            self.SECRET_KEY == self.EVALUATION_SERVICE_KEY or
            self.ADMIN_SECRET_KEY == self.EVALUATION_SERVICE_KEY):
            raise ValueError(
                "FATAL SECURITY CONFIGURATION ERROR: Application secrets (SECRET_KEY, ADMIN_SECRET_KEY, EVALUATION_SERVICE_KEY) "
                "must all be strictly distinct from each other."
            )

        # 2. Strict production checks: require explicit configuration without fallbacks
        if self.ENVIRONMENT.lower() == "production":
            if not self.SECRET_KEY or self.SECRET_KEY in known_placeholders or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "FATAL SECURITY CONFIGURATION ERROR: Insecure, weak, or default SECRET_KEY configured in production mode. "
                    "You must supply a strong SECRET_KEY (at least 32 characters)."
                )

            if not self.ADMIN_SECRET_KEY or self.ADMIN_SECRET_KEY in known_placeholders or len(self.ADMIN_SECRET_KEY) < 32:
                raise ValueError(
                    "FATAL SECURITY CONFIGURATION ERROR: Insecure, weak, or default ADMIN_SECRET_KEY configured in production mode. "
                    "You must supply a strong ADMIN_SECRET_KEY (at least 32 characters)."
                )

            if not self.EVALUATION_SERVICE_KEY or self.EVALUATION_SERVICE_KEY in known_placeholders or len(self.EVALUATION_SERVICE_KEY) < 32:
                raise ValueError(
                    "FATAL SECURITY CONFIGURATION ERROR: Insecure, weak, or default EVALUATION_SERVICE_KEY configured in production mode. "
                    "You must supply a strong EVALUATION_SERVICE_KEY (at least 32 characters)."
                )


settings = Settings()
settings.validate_secrets()
