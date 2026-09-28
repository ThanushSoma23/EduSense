from fastapi import APIRouter
from app.api.v1 import auth, exams, sheets, transcript, marks, publish, student, appeals, admin, evaluation, tutor

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(exams.router, prefix="/exams", tags=["Exams"])
api_router.include_router(sheets.router, tags=["Answer Sheets"])
api_router.include_router(evaluation.router, tags=["Evaluation"])
api_router.include_router(evaluation.kb_router, tags=["Knowledge Base"])
api_router.include_router(transcript.router, tags=["Transcript"])
api_router.include_router(marks.router, tags=["Teacher Award"])
api_router.include_router(publish.router, tags=["Publish"])
api_router.include_router(student.router, tags=["Student Results"])
api_router.include_router(appeals.router, tags=["Appeals"])
api_router.include_router(tutor.router, tags=["AI Tutor"])
