"""
EduSense — OCR & Question Segmentation Service Integration
Bridges EasyOCR, AIML-2 TrOCR, image preprocessing, and robust regex segmentation
into the primary PostgreSQL/SQLite backend application lifecycle.
"""

import re
import io
import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
import cv2
from PIL import Image, ImageOps
import pypdfium2 as pdfium

from app.config import settings

logger = logging.getLogger("app.services.ocr_service")

# Global variables for caching OCR engines in memory
_EASYOCR_READER = None
_LAST_OCR_ERROR: Optional[str] = None

# Comprehensive regex pattern covering standard and handwritten question markers:
# Matches:
#   - Q1, Q1:, Q1., Q-1, Q 1, Q.1
#   - Question 1, QuestiOn 1, QLestion 1, Qvestion 1, Quest 1
#   - Ans 1:, Answer 1:, Ans. 1, Ans: 1
#   - 1., 1), 1:, 1 - at start of line or with space boundary
#   - Standalone number with marks notation: e.g. 5 (10 marks), 1 (5 masks), 5 10_masks
QUESTION_HEADER_PATTERN = re.compile(
    r'(?:^|(?<=\s))(?:(?:Q|Question|QuestiOn|QLestion|Qvestion|Quest|Ans|Answer|\#)\s*[\.\:\-]?\s*(\d+)[\.\:\)\-\s]|(?:O|0)\s*([1-9]\d?)[\.\:\)\-\s]|(\d+)\s*[\.\:\)\-]|(\d+)\s+(?:\(\d+[\s_]*m|\d+[\s_]*m))\s*',
    re.IGNORECASE
)


def get_last_ocr_error() -> Optional[str]:
    """Returns the last error encountered during OCR execution, if any."""
    global _LAST_OCR_ERROR
    return _LAST_OCR_ERROR


def extract_question_number_and_body(text: str) -> Optional[Tuple[int, str]]:
    """
    Check if a text line starts with or contains a recognizable question marker.
    Returns (question_number, remaining_body_text) if matched, else None.
    """
    stripped = text.strip()
    match = QUESTION_HEADER_PATTERN.search(stripped)
    if not match:
        return None

    q_str = match.group(1) or match.group(2) or match.group(3) or match.group(4)
    try:
        q_num = int(q_str)
    except (ValueError, TypeError):
        return None

    # Body is text following the header match
    body = stripped[match.end():].strip()
    return q_num, body


def get_mock_ocr_lines() -> List[Dict[str, Any]]:
    """Deterministic mock OCR output for test suites and offline operation."""
    return [
        {"text": "Q1 Explain deadlock. Deadlock occurs when processes wait for resources held by each other.", "confidence": 0.94},
        {"text": "A deadlock condition requires mutual exclusion, hold and wait, no preemption, and circular wait.", "confidence": 0.92},
        {"text": "Q2 What is a process? A process is a program in execution containing its own address space.", "confidence": 0.88},
        {"text": "Q3 Explain semaphore. Semaphore is used for synchronization.", "confidence": 0.52}
    ]


def extract_document_pages(file_bytes: bytes) -> Tuple[Optional[List[np.ndarray]], Optional[str]]:
    """
    Extracts high-resolution RGB numpy array pages from either PDF or standard image formats.
    Returns (pages_list, None) on success or (None, error_msg) on failure.
    """
    if not file_bytes:
        return None, "Empty file bytes provided."

    # Check for PDF magic bytes
    if file_bytes[:4] == b"%PDF" or b"%PDF" in file_bytes[:1024]:
        try:
            pdf = pdfium.PdfDocument(io.BytesIO(file_bytes))
            if len(pdf) == 0:
                return None, "PDF document contains no renderable pages."
            pages = []
            for i in range(len(pdf)):
                # scale=2 gives ~150-200 DPI, optimal for text detection without OOM
                pil_page = pdf[i].render(scale=2).to_pil().convert("RGB")
                pages.append(np.array(pil_page))
            return pages, None
        except Exception as pdf_err:
            logger.warning(f"Failed to decode PDF: {pdf_err}")
            return None, f"Corrupt or unreadable PDF document: {pdf_err}"

    # Standard image formats (PNG, JPG, WebP, TIFF, BMP)
    try:
        pil_img = Image.open(io.BytesIO(file_bytes))
        # Handle phone camera EXIF orientation rotation
        pil_img = ImageOps.exif_transpose(pil_img)
        pil_img = pil_img.convert("RGB")
        return [np.array(pil_img)], None
    except Exception as img_err:
        logger.warning(f"Failed to decode image bytes: {img_err}")
        return None, "Corrupt or unreadable image file format."


def preprocess_page_for_ocr(img: np.ndarray) -> Tuple[np.ndarray, List[str]]:
    """
    Per-page image enhancement pipeline tailored for EasyOCR CRAFT and CRNN:
    1. Safe aspect-ratio resizing (capping long edge <= 2500px, min edge >= 600px).
    2. Quality checks: blur evaluation (Laplacian variance) and contrast range.
    3. Deskewing within +/-15 degrees using minAreaRect on Otsu projection.
    4. Background illumination flattening (morphological close division).
    5. Gentle median blur for salt/pepper noise reduction preserving thin pen strokes.
    6. Contrast Limited Adaptive Histogram Equalization (CLAHE).
    Never performs harsh 1-bit binarization on the image passed to EasyOCR.
    Returns (enhanced_grayscale_image, quality_flags).
    """
    if img is None or img.size == 0:
        return img, ["corrupt_page"]

    flags = []
    h, w = img.shape[:2]
    max_dim = max(h, w)
    min_dim = min(h, w)

    # 1. Resizing check: scale down if gigantic, scale up if tiny
    working_img = img
    if max_dim > 2500:
        scale = 2500.0 / float(max_dim)
        working_img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    elif min_dim < 600:
        scale = 800.0 / float(min_dim)
        working_img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

    # 2. Grayscale conversion
    if len(working_img.shape) == 3:
        gray = cv2.cvtColor(working_img, cv2.COLOR_RGB2GRAY)
    else:
        gray = working_img.copy()

    # 3. Quality checks
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if lap_var < 50.0:
        flags.append("blurry")

    min_val, max_val, _, _ = cv2.minMaxLoc(gray)
    contrast_range = float(max_val - min_val)
    if contrast_range < 40.0:
        flags.append("low_contrast")

    # 4. Deskewing (only if significant skew detected, clamped to +/-15 deg)
    try:
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) > 50:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90.0 + angle)
            else:
                angle = -angle

            if abs(angle) <= 15.0 and abs(angle) >= 0.5:
                (gh, gw) = gray.shape[:2]
                M = cv2.getRotationMatrix2D((gw // 2, gh // 2), angle, 1.0)
                gray = cv2.warpAffine(gray, M, (gw, gh), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                flags.append(f"deskewed_{round(angle, 1)}deg")
    except Exception as deskew_err:
        logger.debug(f"Deskew skipped: {deskew_err}")

    # 5. Background shadow removal & illumination flattening
    try:
        k_size = min(35, max(15, min(gray.shape[:2]) // 20 | 1))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, k_size))
        bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        norm = cv2.divide(gray, bg, scale=255)
    except Exception:
        norm = gray

    # 6. Denoise with small median blur to preserve stroke edges
    denoised = cv2.medianBlur(norm, 3)

    # 7. Contrast enhancement (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)

    return enhanced, flags


def group_detections_into_lines(detections: List[Any], y_threshold: float = 18.0) -> List[Tuple[str, float]]:
    """
    Reconstructs natural reading lines from unordered EasyOCR CRAFT bounding boxes.
    Sorts top-to-bottom, groups items with vertical overlap into the same horizontal line,
    and sorts words left-to-right within each line.
    """
    if not detections:
        return []

    items = []
    for bbox, text, prob in detections:
        text_str = str(text).strip()
        if not text_str:
            continue
        try:
            ys = [p[1] for p in bbox]
            xs = [p[0] for p in bbox]
            min_y, max_y = min(ys), max(ys)
            cy = (min_y + max_y) / 2.0
            min_x = min(xs)
            height = max_y - min_y
            items.append({
                "text": text_str,
                "prob": float(prob),
                "cy": cy,
                "min_x": min_x,
                "h": height
            })
        except Exception:
            items.append({
                "text": text_str,
                "prob": float(prob),
                "cy": 0.0,
                "min_x": 0.0,
                "h": 20.0
            })

    # Sort strictly by center Y
    items.sort(key=lambda it: it["cy"])

    lines: List[Tuple[str, float]] = []
    current_line = []
    current_cy = None

    for it in items:
        if current_cy is None:
            current_line.append(it)
            current_cy = it["cy"]
        elif abs(it["cy"] - current_cy) <= max(y_threshold, it["h"] * 0.55):
            current_line.append(it)
            current_cy = sum(x["cy"] for x in current_line) / len(current_line)
        else:
            current_line.sort(key=lambda x: x["min_x"])
            line_text = " ".join(x["text"] for x in current_line)
            line_conf = sum(x["prob"] for x in current_line) / len(current_line)
            lines.append((line_text, line_conf))
            current_line = [it]
            current_cy = it["cy"]

    if current_line:
        current_line.sort(key=lambda x: x["min_x"])
        line_text = " ".join(x["text"] for x in current_line)
        line_conf = sum(x["prob"] for x in current_line) / len(current_line)
        lines.append((line_text, line_conf))

    return lines


def run_easyocr_inference(file_bytes: bytes) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Runs real EasyOCR inference on document bytes (PDF or Image) using cached local weights.
    Applies image preprocessing and reading-line reconstruction.
    Returns (lines, None) on success or (None, error_str) on failure.
    Never returns mock lines.
    """
    global _EASYOCR_READER
    if not file_bytes:
        return None, "Empty file bytes provided."

    pages, extract_err = extract_document_pages(file_bytes)
    if extract_err is not None or not pages:
        return None, extract_err or "Failed to decode document."

    try:
        import easyocr

        if _EASYOCR_READER is None:
            logger.info("Initializing EasyOCR reader from local model cache...")
            download_enabled = os.getenv("EASYOCR_DOWNLOAD_ENABLED", "false").lower() in ("true", "1", "yes")
            _EASYOCR_READER = easyocr.Reader(['en'], gpu=False, download_enabled=download_enabled)

        all_lines: List[Dict[str, Any]] = []
        has_quality_warning = False

        for page_idx, page_img in enumerate(pages):
            enhanced_page, quality_flags = preprocess_page_for_ocr(page_img)
            if any(f in quality_flags for f in ["blurry", "low_contrast"]):
                has_quality_warning = True

            results = _EASYOCR_READER.readtext(enhanced_page)
            page_lines = group_detections_into_lines(results)

            for l_text, l_conf in page_lines:
                cleaned = l_text.strip()
                if cleaned:
                    all_lines.append({
                        "text": cleaned,
                        "confidence": round(float(l_conf), 4),
                        "page": page_idx + 1,
                        "quality_flags": quality_flags
                    })

        return all_lines, None
    except Exception as e:
        logger.error(f"EasyOCR execution error: {e}")
        return None, str(e)


def run_trocr_inference(file_bytes: bytes) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Attempts to run real Microsoft TrOCR inference on image bytes via AIML-2.
    Returns (lines, None) on success or (None, error_str) on failure.
    Never returns mock lines.
    """
    if not file_bytes:
        return None, "Empty image bytes provided."

    pages, extract_err = extract_document_pages(file_bytes)
    if extract_err is not None or not pages:
        return None, extract_err or "Failed to decode document."

    try:
        aiml2_dir = str(Path(__file__).resolve().parent.parent.parent.parent / "AIML-2")
        if aiml2_dir not in sys.path:
            sys.path.insert(0, aiml2_dir)

        try:
            from ocr import extract_text_from_sheet, get_trocr_load_error, load_trocr
        except ImportError as imp_err:
            return None, f"AIML-2 OCR module import error: {imp_err}"

        processor, model = load_trocr()
        if processor is None or model is None:
            load_err = get_trocr_load_error() or "TrOCR model or tokenizer dependencies unavailable."
            return None, load_err

        all_lines = []
        for page_img in pages:
            pil_page = Image.fromarray(page_img)
            lines = extract_text_from_sheet(pil_page, use_mock_fallback=False)
            if lines:
                all_lines.extend(lines)

        return all_lines, None
    except Exception as e:
        logger.warning(f"TrOCR execution error: {e}")
        return None, str(e)


def segment_ocr_lines(
    ocr_lines: List[Dict[str, Any]],
    threshold: float = 0.70
) -> List[Dict[str, Any]]:
    """
    Segments OCR line items into question-wise answers with confidence calculation
    and explicit extraction_status (SUCCESS, PARTIAL, FAILED, AMBIGUOUS).
    Handles questions split across pages and mid-line question header transitions.
    """
    if not ocr_lines:
        return []

    segmented: List[Dict[str, Any]] = []
    current_q_num: int = 1
    current_lines: List[str] = []
    current_confs: List[float] = []
    has_seen_header: bool = False
    raw_detected_headers: List[int] = []

    def finalize_block(q_num: int, lines: List[str], confs: List[float]) -> Dict[str, Any]:
        combined_text = " ".join(lines).strip()
        if not combined_text:
            return {
                "question_number": q_num,
                "raw_question_number": q_num,
                "text": "",
                "confidence": 0.0,
                "needs_review": True,
                "extraction_status": "FAILED"
            }

        avg_conf = round(sum(confs) / len(confs), 4) if confs else 0.90
        min_conf = min(confs) if confs else 1.0

        is_low_conf = (avg_conf < threshold) or (min_conf < 0.40)
        is_short = len(combined_text) < 5
        needs_rev = is_low_conf or is_short

        status_label = "PARTIAL" if needs_rev else "SUCCESS"

        return {
            "question_number": q_num,
            "raw_question_number": q_num,
            "text": combined_text,
            "confidence": avg_conf,
            "needs_review": needs_rev,
            "extraction_status": status_label
        }

    for item in ocr_lines:
        text = str(item.get("text", "")).strip()
        conf = float(item.get("confidence", 0.90))
        if not text:
            continue

        # Check for header within the line (handles start and mid-line markers)
        m = QUESTION_HEADER_PATTERN.search(text)
        if m:
            start, end = m.span()
            pre_text = text[:start].strip()
            if pre_text:
                current_lines.append(pre_text)
                current_confs.append(conf)

            if current_lines or has_seen_header:
                segmented.append(finalize_block(current_q_num, current_lines, current_confs))

            q_num_str = m.group(1) or m.group(2) or m.group(3) or m.group(4)
            try:
                new_q_num = int(q_num_str)
            except (ValueError, TypeError):
                new_q_num = current_q_num + 1

            current_q_num = new_q_num
            has_seen_header = True
            raw_detected_headers.append(new_q_num)

            post_text = text[end:].strip()
            current_lines = [post_text] if post_text else []
            current_confs = [conf]
        else:
            current_lines.append(text)
            current_confs.append(conf)

    if current_lines or has_seen_header:
        segmented.append(finalize_block(current_q_num, current_lines, current_confs))

    # Detect duplicate question numbers in segmented output
    seen_q_nums = {}
    for block in segmented:
        qn = block["question_number"]
        seen_q_nums[qn] = seen_q_nums.get(qn, 0) + 1

    for block in segmented:
        qn = block["question_number"]
        if seen_q_nums.get(qn, 0) > 1:
            block["is_ambiguous"] = True
            block["needs_review"] = True
            if block["extraction_status"] == "SUCCESS":
                block["extraction_status"] = "AMBIGUOUS"

    return segmented


def transcribe_and_segment(
    file_bytes: bytes,
    threshold: Optional[float] = None,
    backend: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Main transcription service entry point:
    1. Honors configured OCR_BACKEND ('easyocr', 'trocr', 'mock') unless overridden.
    2. Runs selected OCR engine on document bytes (PDF or image).
    3. Strictly NEVER falls back to mock text when real OCR is selected.
    4. Segments extracted text into question-wise answers with confidence.
    5. Returns (segmented_answers, backend_used).
    """
    global _LAST_OCR_ERROR
    _LAST_OCR_ERROR = None

    review_thresh = threshold if threshold is not None else getattr(settings, "OCR_REVIEW_THRESHOLD", 0.70)

    if not backend or backend.lower() == "auto":
        backend_choice = getattr(settings, "OCR_BACKEND", "easyocr").lower()
    else:
        backend_choice = backend.lower()

    if backend_choice == "mock":
        raw_lines = get_mock_ocr_lines()
        segmented = segment_ocr_lines(raw_lines, threshold=review_thresh)
        return segmented, "mock"

    elif backend_choice == "easyocr":
        lines, err = run_easyocr_inference(file_bytes)
        if err is not None:
            _LAST_OCR_ERROR = err
            logger.error(f"EasyOCR failed: {err}. Mock fallback is disabled for real OCR.")
            return [], "easyocr"
        segmented = segment_ocr_lines(lines or [], threshold=review_thresh)
        return segmented, "easyocr"

    elif backend_choice == "trocr":
        lines, err = run_trocr_inference(file_bytes)
        if err is not None:
            _LAST_OCR_ERROR = err
            logger.error(f"TrOCR failed: {err}. Mock fallback is disabled for real OCR.")
            return [], "trocr"
        segmented = segment_ocr_lines(lines or [], threshold=review_thresh)
        return segmented, "trocr"

    else:
        err_msg = f"Unknown OCR backend '{backend_choice}'. Supported: 'easyocr', 'trocr', 'mock'."
        _LAST_OCR_ERROR = err_msg
        logger.error(err_msg)
        return [], backend_choice


def warmup_ocr() -> bool:
    """
    Pre-initializes the configured OCR engine (e.g. EasyOCR) during application startup
    or container initialization using cached local weights without runtime downloads.
    Returns True if initialized successfully, or False if initialization failed.
    Accurately records any initialization error in _LAST_OCR_ERROR.
    """
    global _EASYOCR_READER, _LAST_OCR_ERROR
    backend = (getattr(settings, "OCR_BACKEND", "easyocr") or "easyocr").lower().strip()
    if backend == "mock":
        return True

    if backend == "easyocr":
        if _EASYOCR_READER is not None:
            return True
        try:
            import easyocr
            logger.info("Pre-warming EasyOCR reader from local model cache...")
            download_enabled = os.getenv("EASYOCR_DOWNLOAD_ENABLED", "false").lower() in ("true", "1", "yes")
            _EASYOCR_READER = easyocr.Reader(['en'], gpu=False, download_enabled=download_enabled)
            return True
        except Exception as e:
            _LAST_OCR_ERROR = f"EasyOCR warmup failed: {str(e)}"
            logger.warning(f"EasyOCR warmup failed: {e}")
            return False

    elif backend == "trocr":
        try:
            aiml2_dir = str(Path(__file__).resolve().parent.parent.parent.parent / "AIML-2")
            if aiml2_dir not in sys.path:
                sys.path.insert(0, aiml2_dir)
            from ocr import load_trocr, get_trocr_load_error
            processor, model = load_trocr()
            if processor is None or model is None:
                _LAST_OCR_ERROR = get_trocr_load_error() or "TrOCR model weights or tokenizer unavailable."
                return False
            return True
        except Exception as e:
            _LAST_OCR_ERROR = f"TrOCR warmup failed: {str(e)}"
            return False

    return True
