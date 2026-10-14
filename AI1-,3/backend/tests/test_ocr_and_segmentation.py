import io
import pytest
import numpy as np
import cv2
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.db.supabase import db
from app.services.ocr import run_ocr, MockOCRBackend, TrOCRBackend
from app.services.segmentation import (
    segment_transcript,
    extract_question_number_and_body,
    QUESTION_HEADER_PATTERN
)

client = TestClient(app)

def test_mock_ocr_backend_output_contract():
    backend = MockOCRBackend()
    lines = backend.recognize(b"dummy_bytes")
    assert len(lines) >= 3
    for line in lines:
        assert "text" in line
        assert "confidence" in line
        assert 0.0 <= line["confidence"] <= 1.0
        assert len(line["text"]) > 0

def test_trocr_backend_graceful_fallback():
    # TrOCR without real weights or in mock environment should gracefully fallback without throwing exception
    trocr = TrOCRBackend(model_name="microsoft/trocr-nonexistent-test-model")
    res = trocr.recognize(b"fake_image_bytes")
    assert isinstance(res, list)
    assert len(res) > 0
    assert "text" in res[0]
    assert "confidence" in res[0]

def test_trocr_horizontal_line_splitting():
    # Synthesize an image with 3 horizontal black text strips on white background
    img = np.ones((300, 400, 3), dtype=np.uint8) * 255
    cv2.putText(img, "Q1 First Line of Answer", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(img, "Second line of Q1 explanation", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(img, "Q2 Second Question Answer", (20, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    trocr = TrOCRBackend()
    line_crops = trocr._split_into_horizontal_lines(img)
    assert len(line_crops) >= 2, f"Expected at least 2 line crops, got {len(line_crops)}"

def test_extract_question_number_and_body_patterns():
    test_cases = [
        ("Q1: A Binary Search Tree", (1, "A Binary Search Tree")),
        ("Q2. Dijkstra algorithm", (2, "Dijkstra algorithm")),
        ("Question 3: Operating System", (3, "Operating System")),
        ("Ans 4: Virtual Memory", (4, "Virtual Memory")),
        ("Answer 5. Thread safety", (5, "Thread safety")),
        ("6) Quick sort partitioning", (6, "Quick sort partitioning")),
        ("7. Merge sort complexity", (7, "Merge sort complexity")),
        ("Q-8: Database indexing", (8, "Database indexing")),
        ("Normal text line with no question marker", None),
    ]

    for raw, expected in test_cases:
        res = extract_question_number_and_body(raw)
        assert res == expected, f"Failed pattern for '{raw}', got {res}"

def test_segment_transcript_grouping_and_stripping():
    ocr_lines = [
        {"text": "Q1: First line of question 1 answer.", "confidence": 0.95},
        {"text": "Second line expanding on question 1.", "confidence": 0.93},
        {"text": "Q2. Question 2 answer is concise.", "confidence": 0.90},
        {"text": "3) Question 3 with another syntax.", "confidence": 0.88},
    ]

    segmented = segment_transcript(ocr_lines)
    assert len(segmented) == 3

    assert segmented[0]["question_number"] == 1
    assert "Q1:" not in segmented[0]["text"]
    assert "First line" in segmented[0]["text"]
    assert "Second line" in segmented[0]["text"]
    assert segmented[0]["ocr_confidence"] == pytest.approx(0.94, abs=0.01)
    assert segmented[0]["needs_review"] is False

    assert segmented[1]["question_number"] == 2
    assert "Q2." not in segmented[1]["text"]
    assert segmented[1]["text"] == "Question 2 answer is concise."

    assert segmented[2]["question_number"] == 3
    assert "3)" not in segmented[2]["text"]

def test_segment_transcript_needs_review_threshold():
    # Low confidence lines should flag needs_review = True
    ocr_lines = [
        {"text": "Q1: Clean handwriting answer.", "confidence": 0.95},
        {"text": "Q2: Illegible blurry handwriting answer.", "confidence": 0.45},
    ]

    segmented = segment_transcript(ocr_lines, review_threshold=0.70)
    assert len(segmented) == 2
    assert segmented[0]["needs_review"] is False
    assert segmented[1]["needs_review"] is True

def test_api_transcribe_endpoint():
    # Create simple PNG in memory
    img = Image.new("RGB", (200, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    # Use teacher login token from test auth or dev bypass
    headers = {"Authorization": "Bearer dev-token-teacher"}
    response = client.post(
        "/api/v1/ocr/transcribe?backend=mock",
        files={"file": ("answersheet.png", buf.getvalue(), "image/png")},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["backend_used"] == "mock"
    assert data["total_questions"] >= 2
    assert len(data["answers"]) >= 2
    assert "overall_confidence" in data
    assert "needs_review" in data

def test_api_sheets_transcribe_creates_db_answers():
    sheet_id = "sheet-test-ocr-001"
    exam_id = "e1111111-1111-1111-1111-111111111111"
    db.answer_sheets[sheet_id] = {
        "id": sheet_id,
        "exam_id": exam_id,
        "student_id": "22222222-2222-2222-2222-222222222222",
        "status": "PREPROCESSED"
    }

    headers = {"Authorization": "Bearer dev-token-teacher"}
    response = client.post(
        f"/api/v1/ocr/sheets/{sheet_id}/transcribe?backend=mock",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sheet_id"] == sheet_id

    # Check that answers were upserted into db.answers
    sheet_answers = [a for a in db.answers.values() if a.get("sheet_id") == sheet_id]
    assert len(sheet_answers) >= 2
    for ans in sheet_answers:
        assert "text" in ans
        assert "ocr_confidence" in ans
        assert "needs_review" in ans
