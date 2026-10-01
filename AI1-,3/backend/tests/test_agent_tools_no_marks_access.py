import inspect
import ast
from pathlib import Path
import pytest
import app.agents.tools as tools_module
import app.api.v1.tutor as tutor_module

def check_ast_for_forbidden_marks_access(source_code: str, file_name: str):
    tree = ast.parse(source_code)

    forbidden_identifiers = ["final_marks", "db.marks", "public.marks"]

    for node in ast.walk(tree):
        # 1. String literal check for .table("marks") or .from_("marks")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr in ["table", "from_"]:
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and arg.value == "marks":
                        raise AssertionError(f"Forbidden table access '.{node.func.attr}(\"marks\")' found in {file_name}!")

        # 2. Function definitions source check
        if isinstance(node, ast.FunctionDef):
            fn_source = ast.get_source_segment(source_code, node) or ""
            for forbidden in forbidden_identifiers:
                assert forbidden not in fn_source, f"Forbidden identifier '{forbidden}' found in {file_name} function '{node.name}'!"

def test_hardened_ast_no_marks_access_in_aiml_and_tutor():
    """
    Hardened AST test scanning tools.py, tutor.py, and all modules under evaluation/ and preprocessing/.
    Forbids 'final_marks', 'db.marks', and string literals .table('marks') / .from_('marks').
    """
    app_dir = Path(__file__).parent.parent / "app"
    target_dirs = [app_dir / "evaluation", app_dir / "preprocessing"]

    files_to_check = [
        Path(tools_module.__file__),
        Path(tutor_module.__file__)
    ]

    for d in target_dirs:
        if d.exists():
            files_to_check.extend(d.glob("*.py"))

    for py_file in files_to_check:
        code = py_file.read_text(encoding="utf-8")
        check_ast_for_forbidden_marks_access(code, py_file.name)

def test_ast_check_negative_test_fails_on_final_marks():
    """Negative test proving that if 'final_marks' is introduced, AST assertion fails."""
    bad_code = """
def bad_tool(answer_id: str, final_marks: float):
    return {"answer_id": answer_id, "final_marks": final_marks}
"""
    with pytest.raises(AssertionError) as exc_info:
        check_ast_for_forbidden_marks_access(bad_code, "bad_tool.py")
    assert "final_marks" in str(exc_info.value)

def test_ast_check_negative_test_fails_on_table_marks_literal():
    """Negative test proving that if .table("marks") is called, AST assertion fails."""
    bad_code = """
def bad_supabase_query(client, answer_id: str):
    return client.table("marks").select("*").eq("answer_id", answer_id).execute()
"""
    with pytest.raises(AssertionError) as exc_info:
        check_ast_for_forbidden_marks_access(bad_code, "bad_query.py")
    assert "marks" in str(exc_info.value)

def test_static_trigger_definition_includes_before_insert_or_update():
    """Static CI check ensuring trigger migration contains 'BEFORE INSERT OR UPDATE ON public.marks'."""
    migrations_dir = Path(__file__).parent.parent.parent / "supabase" / "migrations"
    found_before_insert_update = False
    for sql_file in migrations_dir.glob("*.sql"):
        content = sql_file.read_text(encoding="utf-8")
        if "BEFORE INSERT OR UPDATE ON public.marks" in content:
            found_before_insert_update = True
            break
    assert found_before_insert_update, "Postgres trigger MUST be defined as BEFORE INSERT OR UPDATE ON public.marks!"
