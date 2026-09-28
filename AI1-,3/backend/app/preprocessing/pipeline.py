import os
import hashlib
import logging
from pathlib import Path
from typing import List, Union, Dict, Any
import cv2
import numpy as np
from PIL import Image

from app.preprocessing.schemas import PreprocessingConfig, PreprocessedPage, LineRegion
from app.preprocessing.page_detect import detect_and_warp_page
from app.preprocessing.deskew import deskew_image
from app.preprocessing.denoise import denoise_and_remove_shadows
from app.preprocessing.contrast import enhance_contrast_clahe
from app.preprocessing.regions import extract_line_regions
from app.preprocessing.quality import evaluate_page_quality

logger = logging.getLogger(__name__)

# Output base directory
STORAGE_BASE = Path(__file__).parent.parent.parent / "scratch" / "preprocessed"

def load_image_bytes(input_source: Union[bytes, str, Path]) -> np.ndarray:
    """Load image into RGB numpy array from bytes or path."""
    if isinstance(input_source, (str, Path)):
        img_bgr = cv2.imread(str(input_source))
        if img_bgr is None:
            raise ValueError(f"Failed to read image at path: {input_source}")
        return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    elif isinstance(input_source, bytes):
        nparr = np.frombuffer(input_source, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise ValueError("Corrupt file or invalid image bytes.")
        return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    raise ValueError("Unsupported input source type.")

def preprocess_single_page(
    image_input: Union[bytes, str, Path],
    page_number: int = 1,
    institution_id: str = "default_inst",
    exam_id: str = "default_exam",
    sheet_id: str = "default_sheet",
    config: PreprocessingConfig = PreprocessingConfig()
) -> PreprocessedPage:
    """
    Pure pipeline function for a single page. Idempotent and configurable.
    Saves outputs under storage: {institution}/{exam}/{sheet}/pages/{n}/
    """
    img = load_image_bytes(image_input)

    # 1. Ingest: Cap long side ~2500px
    h, w = img.shape[:2]
    max_side = max(h, w)
    if max_side > config.max_long_side:
        scale = config.max_long_side / float(max_side)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    # 2. Page detection & perspective warp
    page_detected = True
    if config.enable_page_detect:
        img, page_detected = detect_and_warp_page(img)

    # 3. Deskew
    skew_deg = 0.0
    if config.enable_deskew:
        img, skew_deg = deskew_image(img)

    # 4. Denoise & remove background shadows
    if config.enable_denoise:
        img = denoise_and_remove_shadows(img)

    # 5. Contrast CLAHE & Binarisation
    enhanced_gray, binarised = enhance_contrast_clahe(img)

    # 6. Region splitting into line bboxes
    line_bboxes = extract_line_regions(binarised, page_number=page_number) if config.enable_region_split else []

    # 7. Quality gate evaluation
    quality_score, flags = evaluate_page_quality(img, skew_deg=skew_deg, page_detected=page_detected)

    # Save outputs to disk under {institution}/{exam}/{sheet}/pages/{n}/
    page_dir = STORAGE_BASE / institution_id / exam_id / sheet_id / "pages" / str(page_number)
    page_dir.mkdir(parents=True, exist_ok=True)

    clean_path = page_dir / "clean.png"
    binary_path = page_dir / "binary.png"

    cv2.imwrite(str(clean_path), enhanced_gray)
    cv2.imwrite(str(binary_path), binarised)

    line_regions = []
    for idx, reg in enumerate(line_bboxes):
        x, y, lw, lh = reg["bbox"]
        crop = enhanced_gray[y:y+lh, x:x+lw]
        crop_path = page_dir / f"line_{idx+1}.png"
        if crop.size > 0:
            cv2.imwrite(str(crop_path), crop)
            line_regions.append(LineRegion(bbox=reg["bbox"], crop_path=str(crop_path)))

    return PreprocessedPage(
        page_number=page_number,
        clean_path=str(clean_path),
        binary_path=str(binary_path),
        page_detected=page_detected,
        skew_deg=skew_deg,
        quality_score=quality_score,
        flags=flags,
        line_regions=line_regions
    )

def preprocess_sheet(
    input_sources: List[Union[bytes, str, Path]],
    institution_id: str = "default_inst",
    exam_id: str = "default_exam",
    sheet_id: str = "default_sheet",
    config: PreprocessingConfig = PreprocessingConfig()
) -> List[PreprocessedPage]:
    """Preprocess multi-page answer sheet."""
    pages = []
    for idx, src in enumerate(input_sources):
        page = preprocess_single_page(
            image_input=src,
            page_number=idx + 1,
            institution_id=institution_id,
            exam_id=exam_id,
            sheet_id=sheet_id,
            config=config
        )
        pages.append(page)
    return pages
