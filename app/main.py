import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import engine, Base
from app.api.v1.router import api_v1_router
# Import all models to ensure metadata registration
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    In development/testing modes, auto-creates missing database tables for convenience.
    In production mode, automatic table creation is strictly bypassed; Alembic migrations must be used.
    """
    if settings.ENVIRONMENT.lower() in ["development", "testing"]:
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            print(f"[Lifespan Notice] Dev table auto-creation skipped: {e}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "EduSense AI — Automated Answer Evaluation System Backend API. "
        "Provides authentication, examination data management, answer sheet submission tracking, "
        "AI evaluation output integration, teacher review with final-mark approval, and audit history."
    ),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS Middleware using explicit environment-configured trusted origins (No Wildcards)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Service-Key", "X-Admin-Secret"],
)

# Global Exception Handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred.",
            "error_type": exc.__class__.__name__
        },
    )

# Include API v1 Routers
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["System Health"])
def health_check():
    return {
        "status": "healthy",
        "app_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/", include_in_schema=False)
def root():
    return {
        "message": "Welcome to EduSense AI Backend API",
        "docs_url": "/docs",
        "health_check": "/health"
    }
