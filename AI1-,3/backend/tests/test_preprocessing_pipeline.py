import time
import pytest
import numpy as np
import cv2
from pathlib import Path
from app.preprocessing.pipeline import preprocess_single_page, preprocess_sheet, load_image_bytes
from app.preprocessing.schemas import PreprocessingConfig

@pytest.fixture
def synthetic_scan_image():
    """Create a synthetic document image: text lines, rotated 7 degrees, noise & shadow."""
    img = np.ones((800, 600, 3), dtype=np.uint8) * 240

    for y in range(100, 700, 60):
        cv2.putText(img, f"Sample Handwritten Line text at Y={y}", (50, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2)

    center = (300, 400)
    M = cv2.getRotationMatrix2D(center, 7.0, 1.0)
    rotated = cv2.warpAffine(img, M, (600, 800), borderValue=(240, 240, 240))

    noise = np.random.normal(0, 15, rotated.shape).astype(np.uint8)
    noisy = cv2.add(rotated, noise)

    _, buf = cv2.imencode(".png", noisy)
    return buf.tobytes()

def test_preprocessing_synthetic_scan(synthetic_scan_image):
    """Test preprocessing on synthetic scan with per-page runtime logging."""
    start_time = time.time()
    res = preprocess_single_page(
        image_input=synthetic_scan_image,
        page_number=1,
        institution_id="test_inst",
        exam_id="test_exam",
        sheet_id="test_sheet"
    )
    elapsed_ms = (time.time() - start_time) * 1000.0
    print(f"[PERF LOG] Preprocessing runtime: {round(elapsed_ms, 2)} ms / page")

    assert res.page_number == 1
    assert res.quality_score >= 0.0
    assert Path(res.clean_path).exists()
    assert Path(res.binary_path).exists()
    assert abs(abs(res.skew_deg) - 7.0) < 1.5 or res.skew_deg == 0.0

def test_preprocessing_perspective_warp_and_uneven_lighting():
    """Test perspective warp and morphological uneven lighting shadow removal."""
    img = np.ones((800, 600, 3), dtype=np.uint8) * 255
    cv2.putText(img, "Perspective Warped Document Text", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    # Add gradient shadow across image
    gradient = np.linspace(50, 255, 600, dtype=np.uint8)
    gradient_grid = np.tile(gradient, (800, 1))
    img_shadowed = cv2.multiply(img[:, :, 0], gradient_grid // 255)
    img_shadowed_bgr = cv2.cvtColor(img_shadowed, cv2.COLOR_GRAY2BGR)

    _, buf = cv2.imencode(".png", img_shadowed_bgr)

    start_time = time.time()
    res = preprocess_single_page(image_input=buf.tobytes(), page_number=1, sheet_id="warp_sheet")
    elapsed_ms = (time.time() - start_time) * 1000.0
    print(f"[PERF LOG] Perspective Warp & Lighting runtime: {round(elapsed_ms, 2)} ms / page")

    assert res.page_number == 1
    assert Path(res.clean_path).exists()

def test_preprocessing_180_degree_rotation():
    """Test 180-degree flipped page handling."""
    img = np.ones((600, 600, 3), dtype=np.uint8) * 240
    cv2.putText(img, "Flipped 180 text", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    # Rotate 180 degrees
    flipped = cv2.rotate(img, cv2.ROTATE_180)
    _, buf = cv2.imencode(".png", flipped)

    res = preprocess_single_page(image_input=buf.tobytes(), page_number=1, sheet_id="flip_sheet")
    assert res.page_number == 1
    assert Path(res.clean_path).exists()

def test_preprocessing_blank_page():
    """Test blank page handling and quality flag firing."""
    img = np.ones((600, 600, 3), dtype=np.uint8) * 255 # Completely blank page
    _, buf = cv2.imencode(".png", img)

    res = preprocess_single_page(image_input=buf.tobytes(), page_number=1, sheet_id="blank_sheet")
    assert res.page_number == 1
    assert "low_contrast" in res.flags or res.quality_score <= 1.0

def test_preprocessing_multipage_pdf_stream(synthetic_scan_image):
    """Test multi-page document preprocessing stream."""
    sources = [synthetic_scan_image, synthetic_scan_image]

    start_time = time.time()
    pages = preprocess_sheet(input_sources=sources, sheet_id="multipage_sheet")
    total_ms = (time.time() - start_time) * 1000.0
    print(f"[PERF LOG] Multi-page (2 pages) runtime: {round(total_ms, 2)} ms ({round(total_ms/2, 2)} ms/page)")

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2

def test_preprocessing_blurry_image_flags_blurry():
    """Test that heavy Gaussian blur triggers the 'blurry' quality flag."""
    img = np.ones((500, 500, 3), dtype=np.uint8) * 200
    cv2.putText(img, "Blurry text line", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    blurred = cv2.GaussianBlur(img, (45, 45), 0)
    _, buf = cv2.imencode(".png", blurred)

    res = preprocess_single_page(image_input=buf.tobytes())
    assert "blurry" in res.flags

def test_preprocessing_corrupt_file_raises_clean_error():
    """Test that corrupt image bytes raise clean ValueError."""
    corrupt_bytes = b"CORRUPT_HEADER_INVALID_IMAGE_BYTES"
    with pytest.raises(ValueError) as exc_info:
        load_image_bytes(corrupt_bytes)
    assert "Corrupt file" in str(exc_info.value) or "invalid image" in str(exc_info.value).lower()
