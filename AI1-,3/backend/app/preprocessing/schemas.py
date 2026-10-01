from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class PreprocessingConfig:
    max_long_side: int = 2500
    enable_page_detect: bool = True
    enable_deskew: bool = True
    enable_denoise: bool = True
    enable_contrast: bool = True
    enable_region_split: bool = True
    enable_quality_gate: bool = True

@dataclass
class LineRegion:
    bbox: List[int] # [x, y, w, h]
    crop_path: str

@dataclass
class PreprocessedPage:
    page_number: int
    clean_path: str
    binary_path: str
    page_detected: bool
    skew_deg: float
    quality_score: float
    flags: List[str] = field(default_factory=list)
    line_regions: List[LineRegion] = field(default_factory=list)
