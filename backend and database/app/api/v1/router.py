from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.exams import router as exams_router
from app.api.v1.submissions import router as submissions_router
from app.api.v1.evaluations import router as evaluations_router
from app.api.v1.final_marks import router as final_marks_router
from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.adapters import adapters_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(exams_router)
api_v1_router.include_router(submissions_router)
api_v1_router.include_router(evaluations_router)
api_v1_router.include_router(final_marks_router)
api_v1_router.include_router(audit_logs_router)
api_v1_router.include_router(adapters_router)
