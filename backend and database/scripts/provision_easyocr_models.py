"""
EduSense AI — EasyOCR Official Model Provisioner.

Downloads, verifies (MD5), and unpacks official EasyOCR pre-trained model weights
for offline inference in CI environments, container builds, and local development.
Does not commit heavy binary weights to Git.
"""

from __future__ import annotations

import hashlib
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

# Official EasyOCR release assets hosted on GitHub releases (stable upstream)
# The expected MD5 checksums match the unzipped .pth weights used by EasyOCR
MODELS = [
    {
        "filename": "craft_mlt_25k.pth",
        "zip_name": "craft_mlt_25k.zip",
        "url": "https://github.com/JaidedAI/EasyOCR/releases/download/pre-v1.1.6/craft_mlt_25k.zip",
        "expected_pth_md5": "2f8227d2def4037cdb3b34389dcf9ec1",
    },
    {
        "filename": "english_g2.pth",
        "zip_name": "english_g2.zip",
        "url": "https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/english_g2.zip",
        "expected_pth_md5": "5864788e1821be9e454ec108d61b887d",
    },
]


def compute_md5(file_path: Path) -> str:
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            md5.update(chunk)
    return md5.hexdigest()


def provision_models(target_dir: Path | None = None) -> bool:
    if target_dir is None:
        custom = os.getenv("EASYOCR_MODEL_DIR")
        if custom:
            target_dir = Path(custom)
        else:
            target_dir = Path.home() / ".EasyOCR" / "model"

    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"Provisioning EasyOCR weights to: {target_dir}")

    for item in MODELS:
        final_pth = target_dir / item["filename"]
        if final_pth.exists() and final_pth.stat().st_size > 1000:
            actual_md5 = compute_md5(final_pth)
            if actual_md5 == item["expected_pth_md5"]:
                print(f"[OK] {item['filename']} already exists ({final_pth.stat().st_size:,} bytes, md5={actual_md5}). Skipping download.")
                continue
            else:
                print(f"[WARN] Existing {item['filename']} checksum mismatch ({actual_md5}). Re-downloading...")
                final_pth.unlink(missing_ok=True)

        temp_zip = target_dir / item["zip_name"]
        print(f"Downloading {item['zip_name']} from {item['url']} ...")

        req = urllib.request.Request(
            item["url"],
            headers={"User-Agent": "EduSense-CI-Provisioner/1.0"}
        )
        with urllib.request.urlopen(req, timeout=180) as response, open(temp_zip, "wb") as out_file:
            while chunk := response.read(65536):
                out_file.write(chunk)

        print(f"Extracting {item['zip_name']} to {target_dir} ...")
        with zipfile.ZipFile(temp_zip, "r") as zip_ref:
            zip_ref.extractall(target_dir)

        temp_zip.unlink(missing_ok=True)

        if not final_pth.exists():
            raise FileNotFoundError(f"Expected extracted file {final_pth} not found after extraction!")

        actual_md5 = compute_md5(final_pth)
        if actual_md5 != item["expected_pth_md5"]:
            final_pth.unlink(missing_ok=True)
            raise ValueError(
                f"Checksum mismatch for extracted {item['filename']}!\n"
                f"Expected: {item['expected_pth_md5']}\n"
                f"Actual:   {actual_md5}"
            )
        print(f"[OK] Extracted and verified {item['filename']} successfully ({final_pth.stat().st_size:,} bytes, md5={actual_md5}).")

    print("\nAll required EasyOCR model weights provisioned and verified.")
    return True


if __name__ == "__main__":
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    try:
        provision_models(dest)
    except Exception as exc:
        print(f"ERROR: Failed to provision EasyOCR models: {exc}", file=sys.stderr)
        sys.exit(1)
