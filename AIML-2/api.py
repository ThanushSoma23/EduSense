"""
==============================================================================
AIML-2: FastAPI Transcription Microservice
Project: EduSense AI
Endpoint: POST /transcribe
==============================================================================

How to run:
  uvicorn api:app --reload

Interactive Swagger Documentation:
  http://127.0.0.1:8000/docs
==============================================================================
"""

import os
import sys
import shutil
import tempfile
import logging
from typing import Optional

# Ensure the current directory is in sys.path so direct and relative imports work
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pipeline import transcribe

logger = logging.getLogger("AIML2.API")

# Initialize FastAPI application
app = FastAPI(
    title="EduSense AIML-2: Handwritten OCR & Question Segmentation",
    description=(
        "Microservice responsible for: "
        "1. Handwritten OCR via Microsoft TrOCR. "
        "2. Question segmentation (Q1, Q2, Q3...). "
        "3. Confidence estimation from decoder token probabilities. "
        "4. needsReview quality flagging for teacher review. "
        "Produces question-wise JSON for AIML-3 semantic evaluation."
    ),
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    """Service health and info check."""
    return {
        "service": "EduSense AIML-2",
        "description": "Handwritten OCR & Question Segmentation",
        "status": "online",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/transcribe", status_code=status.HTTP_200_OK)
async def transcribe_image_endpoint(
    file: UploadFile = File(..., description="Uploaded student answer sheet image file (JPEG, PNG, etc.)"),
    answerSheetId: Optional[str] = Query(default="AS001", description="Identifier for the answer sheet"),
    threshold: Optional[float] = Query(default=0.70, description="Confidence threshold below which needsReview is flagged")
):
    """
    POST /transcribe

    Step 1: Receive the uploaded image file.
    Step 2: Save it to a temporary file on disk.
    Step 3: Send it to the AIML-2 transcription pipeline.
    Step 4: Return question-wise JSON format.
    Step 5: Safely delete the temporary file after processing.
    """
    # Validate uploaded file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload."
        )

    # Validate file extension
    valid_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff")
    if not file.filename.lower().endswith(valid_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image format. Allowed formats: {', '.join(valid_extensions)}"
        )

    # Step 2: Save uploaded image temporarily
    temp_dir = tempfile.gettempdir()
    file_extension = os.path.splitext(file.filename)[1] or ".jpg"
    temp_file_path = os.path.join(temp_dir, f"edusense_aiml2_{os.getpid()}_{file.filename}")

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Check if file has zero bytes
        if os.path.getsize(temp_file_path) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes)."
            )

        # Step 3 & 4: Run AIML-2 pipeline
        result = transcribe(
            image_path=temp_file_path,
            answer_sheet_id=answerSheetId or "AS001",
            threshold=threshold if threshold is not None else 0.70
        )
        return result

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error during transcription: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AIML-2 transcription failed: {str(error)}"
        )

    finally:
        # Step 5: Safely clean up temporary file
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as cleanup_err:
                logger.warning(f"Failed to delete temp file {temp_file_path}: {cleanup_err}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
