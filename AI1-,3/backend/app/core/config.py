import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field

ROOT_ENV = Path(__file__).resolve().parents[4] / ".env"
LOCAL_ENV = Path(__file__).resolve().parents[2] / ".env"
if ROOT_ENV.exists():
    load_dotenv(ROOT_ENV, override=False)
if LOCAL_ENV.exists():
    load_dotenv(LOCAL_ENV, override=False)

class Settings(BaseSettings):
    APP_ENV: str = Field(default_factory=lambda: os.getenv("APP_ENV", "dev"))
    PROJECT_NAME: str = Field(default="EduSense AI")
    API_V1_STR: str = Field(default="/api/v1")

    # Registration & Role Switch Controls
    AUTO_APPROVE_TEACHERS: bool = Field(
        default_factory=lambda: (os.getenv("APP_ENV", "dev") == "dev" and os.getenv("AUTO_APPROVE_TEACHERS", "false").lower() == "true")
    )
    VITE_DEV_ROLE_SWITCH: bool = Field(
        default_factory=lambda: (os.getenv("APP_ENV", "dev") == "dev" and os.getenv("VITE_DEV_ROLE_SWITCH", "false").lower() == "true")
    )
    
    # JWT Secret Key (supports SUPABASE_JWT_SECRET or SECRET_KEY)
    SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_JWT_SECRET") or os.getenv("SECRET_KEY", "edusense_super_secret_jwt_key_change_in_production")
    )
    SUPABASE_JWT_SECRET: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_JWT_SECRET", "")
    )
    ALGORITHM: str = Field(default="HS256")
    
    # Supabase Credentials (supports explicit key names)
    SUPABASE_URL: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_URL", "")
    )
    SUPABASE_ANON_KEY: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_ANON_KEY") or os.getenv("VITE_SUPABASE_ANON_KEY", "")
    )
    SUPABASE_SERVICE_ROLE_KEY: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")
    )
    SUPABASE_KEY: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")
    )
    
    # OCR & LLM
    OCR_BACKEND: str = Field(default_factory=lambda: os.getenv("OCR_BACKEND", "easyocr"))
    OCR_REVIEW_THRESHOLD: float = Field(default_factory=lambda: float(os.getenv("OCR_REVIEW_THRESHOLD", "0.70")))
    GEMINI_API_KEY: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    GEMINI_MODEL: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
    ENABLE_TUTOR: bool = Field(default=False)

    class Config:
        env_file = [str(ROOT_ENV), str(LOCAL_ENV), ".env"]
        extra = "ignore"

settings = Settings()
