"""
EduSense AI - Image Preprocessing CLI Tool
Usage: python -m app.preprocessing.cli in.jpg out_dir/
"""

import sys
import argparse
from pathlib import Path
import cv2
import numpy as np
from app.preprocessing.pipeline import preprocess_single_page

def main():
    parser = argparse.ArgumentParser(description="EduSense AI Preprocessing Debug CLI")
    parser.add_argument("input_image", type=str, help="Path to input image file")
    parser.add_argument("output_dir", type=str, help="Path to output debug directory")

    args = parser.parse_args()
    in_path = Path(args.input_image)
    out_dir = Path(args.output_dir)

    if not in_path.exists():
        print(f"Error: Input file '{in_path}' does not exist.")
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing '{in_path}'...")
    res = preprocess_single_page(
        image_input=in_path,
        page_number=1,
        institution_id="debug_inst",
        exam_id="debug_exam",
        sheet_id="debug_sheet"
    )

    # Generate before/after side-by-side debug comparison image
    orig_img = cv2.imread(str(in_path))
    clean_img = cv2.imread(res.clean_path)

    if orig_img is not None and clean_img is not None:
        h, w = clean_img.shape[:2]
        orig_resized = cv2.resize(orig_img, (w, h))

        if len(clean_img.shape) == 2 or clean_img.shape[2] == 1:
            clean_bgr = cv2.cvtColor(clean_img, cv2.COLOR_GRAY2BGR)
        else:
            clean_bgr = clean_img

        comparison = np.hstack((orig_resized, clean_bgr))
        comp_path = out_dir / "before_after_debug.png"
        cv2.imwrite(str(comp_path), comparison)
        print(f"[OK] Saved side-by-side comparison to '{comp_path}'")

    print(f"Preprocessing completed:")
    print(f"  Page Detected: {res.page_detected}")
    print(f"  Skew Deg: {res.skew_deg}°")
    print(f"  Quality Score: {res.quality_score}")
    print(f"  Flags: {res.flags}")
    print(f"  Line Regions Extracted: {len(res.line_regions)}")
    print(f"  Clean Image Output: {res.clean_path}")

if __name__ == "__main__":
    main()
