import ast
from pathlib import Path
import pytest

def test_aiml_modules_no_final_marks_write():
    """
    CI test scanning all python files in backend/app/ for write operations to 'final_marks'.
    Forbidden: assigning to attributes/dict keys named 'final_marks' or inserting into 'marks' table.
    """
    app_dir = Path(__file__).parent.parent / "app"
    forbidden_writes = ["final_marks =", "'final_marks':", '"final_marks":', "db.marks["]

    scanned_files = 0
    for py_file in app_dir.rglob("*.py"):
        # Skip the explicit teacher award endpoint in auth/marks.py or db helper award_marks function
        if py_file.name in ["marks.py", "supabase.py"]:
            continue

        content = py_file.read_text(encoding="utf-8")
        scanned_files += 1

        for forbidden in forbidden_writes:
            assert forbidden not in content, (
                f"Forbidden write signature '{forbidden}' found in AIML module file: {py_file}!"
            )

    assert scanned_files > 0, "No AIML python files were scanned."
