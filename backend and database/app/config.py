import os
import secrets
from pathlib import Path
from typing import List, Set, Any
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
LOCAL_ENV = Path(__file__).resolve().parents[1] / ".env"
if ROOT_ENV.exists():
    load_dotenv(ROOT_ENV, override=False)
if LOCAL_ENV.exists():
    load_dotenv(LOCAL_ENV, override=False)

DEFAULT_DEV_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:4173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173"
]


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
    CORS_ORIGINS: List[str] = DEFAULT_DEV_CORS_ORIGINS

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(origin).strip() for origin in parsed if str(origin).strip()]
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, (list, tuple, set)):
            return [str(origin).strip() for origin in v if str(origin).strip()]
        return DEFAULT_DEV_CORS_ORIGINS

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # AI Model Settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # OCR Settings
    OCR_BACKEND: str = os.getenv("OCR_BACKEND", "easyocr")
    OCR_REVIEW_THRESHOLD: float = float(os.getenv("OCR_REVIEW_THRESHOLD", "0.70"))
    WARMUP_OCR_ON_STARTUP: bool = os.getenv("WARMUP_OCR_ON_STARTUP", "false").lower() in ("true", "1", "yes")
    EASYOCR_MODEL_DIR: str = os.getenv("EASYOCR_MODEL_DIR", "")

    # Storage Configuration (Local vs S3-Compatible Cloud Storage)
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")
    STORAGE_LOCAL_DIR: str = os.getenv("STORAGE_LOCAL_DIR", "uploads")
    STORAGE_S3_BUCKET: str = os.getenv("STORAGE_S3_BUCKET", "")
    STORAGE_S3_ENDPOINT: str = os.getenv("STORAGE_S3_ENDPOINT", "")
    STORAGE_S3_REGION: str = os.getenv("STORAGE_S3_REGION", "us-east-1")
    STORAGE_S3_ACCESS_KEY: str = os.getenv("STORAGE_S3_ACCESS_KEY", "")
    STORAGE_S3_SECRET_KEY: str = os.getenv("STORAGE_S3_SECRET_KEY", "")
    STORAGE_S3_PUBLIC_BASE_URL: str = os.getenv("STORAGE_S3_PUBLIC_BASE_URL", "")

    # Email & Notification Settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAILS_FROM_EMAIL: str = os.getenv("EMAILS_FROM_EMAIL", "notifications@edusense.ai")
    EMAILS_FROM_NAME: str = os.getenv("EMAILS_FROM_NAME", "EduSense Assessment")
    FRONTEND_BASE_URL: str = os.getenv("FRONTEND_BASE_URL", "http://localhost:4173")

    # Academic Structure Settings
    MIN_SEMESTER: int = int(os.getenv("MIN_SEMESTER", "1"))
    MAX_SEMESTER: int = int(os.getenv("MAX_SEMESTER", "8"))

    model_config = SettingsConfigDict(
        env_file=[str(ROOT_ENV), str(LOCAL_ENV), ".env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def model_post_init(self, __context: Any) -> None:
        self.validate_secrets()

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

        # 3. Storage configuration validation (all environments)
        backend_lower = self.STORAGE_BACKEND.lower()
        if backend_lower not in ("local", "s3"):
            raise ValueError(
                f"FATAL STORAGE CONFIGURATION ERROR: Unsupported STORAGE_BACKEND '{self.STORAGE_BACKEND}'. "
                f"Supported backends are 'local' or 's3'."
            )
        if backend_lower == "s3":
            if not self.STORAGE_S3_BUCKET or not self.STORAGE_S3_BUCKET.strip():
                raise ValueError(
                    "FATAL STORAGE CONFIGURATION ERROR: STORAGE_BACKEND is set to 's3', but STORAGE_S3_BUCKET is empty. "
                    "You must provide a valid STORAGE_S3_BUCKET."
                )

        # 4. Strict production checks: require explicit configuration without fallbacks
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

            # CORS origin validation in production (Safeguard 1)
            if not self.CORS_ORIGINS:
                raise ValueError(
                    "FATAL SECURITY CONFIGURATION ERROR: In production mode, CORS_ORIGINS must be explicitly configured "
                    "with trusted client domains (e.g. 'https://edusense.example.com')."
                )

            if any(origin in ("*", "'*'", '"*"') for origin in self.CORS_ORIGINS):
                raise ValueError(
                    "FATAL SECURITY CONFIGURATION ERROR: In production mode, wildcard CORS origin '*' is strictly prohibited "
                    "because authenticated requests with credentials/cookies cannot safely accept wildcard origins."
                )


settings = Settings()
settings.validate_secrets()
