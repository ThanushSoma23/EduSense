import logging
import uuid
from typing import Dict, Any, List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class InMemoryDatabase:
    def __init__(self):
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self.exams: Dict[str, Dict[str, Any]] = {}
        self.questions: Dict[str, Dict[str, Any]] = {}
        self.answer_sheets: Dict[str, Dict[str, Any]] = {}
        self.answers: Dict[str, Dict[str, Any]] = {}
        self.evaluations: Dict[str, Dict[str, Any]] = {}
        self.marks: Dict[str, Dict[str, Any]] = {}
        self.publications: Dict[str, Dict[str, Any]] = {}
        self.kb_sources: Dict[str, Dict[str, Any]] = {}
        self.kb_chunks: Dict[str, Dict[str, Any]] = {}
        self.appeals: Dict[str, Dict[str, Any]] = {}
        self.colleges: Dict[str, Dict[str, Any]] = {}
        self.college_access_codes: Dict[str, Dict[str, Any]] = {}
        self.teacher_subjects: Dict[str, Dict[str, Any]] = {}
        self._seed_initial_data()

    def _seed_initial_data(self):
        # Seed College
        c_id = "c1111111-1111-1111-1111-111111111111"
        self.colleges[c_id] = {
            "id": c_id,
            "name": "Stanford Institute of Technology",
            "code": "STANFORD"
        }
        self.college_access_codes["code-1"] = {
            "id": "code-1",
            "college_id": c_id,
            "code": "TEACH2026",
            "is_active": True
        }

        # Admin profile
        self.profiles["admin-1111-1111-1111-111111111111"] = {
            "id": "admin-1111-1111-1111-111111111111",
            "full_name": "System Administrator",
            "email": "admin@edusense.ai",
            "role": "admin",
            "status": "active"
        }

        # Teacher profile
        self.profiles["11111111-1111-1111-1111-111111111111"] = {
            "id": "11111111-1111-1111-1111-111111111111",
            "full_name": "Prof. Sarah Jenkins",
            "email": "teacher@edusense.ai",
            "role": "teacher",
            "college_id": c_id,
            "status": "active"
        }

        # Student profiles
        self.profiles["22222222-2222-2222-2222-222222222222"] = {
            "id": "22222222-2222-2222-2222-222222222222",
            "full_name": "Alex Rivera",
            "email": "alex@edusense.ai",
            "roll_number": "CS-2024-001",
            "college_id": c_id,
            "department": "Computer Science",
            "semester": 6,
            "role": "student",
            "status": "active"
        }
        self.profiles["33333333-3333-3333-3333-333333333333"] = {
            "id": "33333333-3333-3333-3333-333333333333",
            "full_name": "Maya Patel",
            "email": "maya@edusense.ai",
            "roll_number": "CS-2024-002",
            "college_id": c_id,
            "department": "Computer Science",
            "semester": 6,
            "role": "student",
            "status": "active"
        }

        # Seed Exam
        exam_id = "e1111111-1111-1111-1111-111111111111"
        self.exams[exam_id] = {
            "id": exam_id,
            "title": "Data Structures & Algorithms Final",
            "subject": "Computer Science",
            "code": "CS-301",
            "teacher_id": "11111111-1111-1111-1111-111111111111"
        }

        # Seed Questions
        self.questions["a1111111-1111-1111-1111-111111111111"] = {
            "id": "a1111111-1111-1111-1111-111111111111",
            "exam_id": exam_id,
            "number": 1,
            "text": "Explain the concept of Binary Search Tree (BST) insertion and time complexity.",
            "max_marks": 5.0,
            "model_answer": "A Binary Search Tree (BST) insertion starts at the root node. If the new value is less than current node, traverse left; if greater, traverse right. Repeat until an empty spot is found, then insert. Average complexity: O(log n), worst case: O(n).",
            "concepts": [
                {"id": "c1", "label": "Root comparison"},
                {"id": "c2", "label": "Left/Right traversal condition"},
                {"id": "c3", "label": "O(log n) average time complexity"},
                {"id": "c4", "label": "O(n) worst-case time complexity"}
            ]
        }
        self.questions["a2222222-2222-2222-2222-222222222222"] = {
            "id": "a2222222-2222-2222-2222-222222222222",
            "exam_id": exam_id,
            "number": 2,
            "text": "What is Dijkstra's Algorithm and what is its primary limitation?",
            "max_marks": 5.0,
            "model_answer": "Dijkstra's Algorithm is a greedy single-source shortest path algorithm for weighted graphs. It repeatedly selects unvisited node with minimum tentative distance. Limitation: Fails on graphs with negative edge weights.",
            "concepts": [
                {"id": "c21", "label": "Greedy single-source algorithm"},
                {"id": "c22", "label": "Priority queue / Min distance selection"},
                {"id": "c23", "label": "Negative edge weights limitation"}
            ]
        }
        self.questions["a3333333-3333-3333-3333-333333333333"] = {
            "id": "a3333333-3333-3333-3333-333333333333",
            "exam_id": exam_id,
            "number": 3,
            "text": "Explain the key differences between a Process and a Thread.",
            "max_marks": 5.0,
            "model_answer": "Process: independent address space, separate memory. Thread: lightweight unit inside process sharing address space and heap, but having own stack and registers.",
            "concepts": [
                {"id": "c31", "label": "Process independent address space"},
                {"id": "c32", "label": "Thread shared memory/heap"},
                {"id": "c33", "label": "Thread program counter and stack"},
                {"id": "c34", "label": "Context switch performance comparison"}
            ]
        }

    def award_marks(self, answer_id: str, final_marks: float, awarded_by: str, award_source: str = "manual", remarks: Optional[str] = None) -> Dict[str, Any]:
        awarder = self.profiles.get(awarded_by)
        if not awarder or awarder.get("role") != "teacher":
            raise ValueError("Unauthorized: Only users with role teacher can set final_marks.")

        mark_id = f"m-{uuid.uuid4()}"
        existing = next((m for m in self.marks.values() if m.get("answer_id") == answer_id), None)
        if existing:
            mark_id = existing["id"]

        mark_record = {
            "id": mark_id,
            "answer_id": answer_id,
            "final_marks": final_marks,
            "awarded_by": awarded_by,
            "award_source": award_source,
            "remarks": remarks
        }
        self.marks[mark_id] = mark_record
        return mark_record

def init_db():
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY or "your-supabase" in settings.SUPABASE_URL:
        if settings.APP_ENV != "dev":
            raise RuntimeError(
                f"FATAL: Missing SUPABASE_URL/SUPABASE_KEY credentials in non-dev mode (APP_ENV='{settings.APP_ENV}'). "
                "In-memory DB fallback is restricted to APP_ENV='dev'."
            )
        logger.info("Initializing EduSense AI with local In-Memory Database (APP_ENV='dev').")
        return InMemoryDatabase()
    else:
        try:
            from supabase import create_client
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            logger.info("Connected to live Supabase database.")
            return client
        except Exception as e:
            if settings.APP_ENV != "dev":
                raise RuntimeError(f"FATAL: Failed to connect to Supabase in APP_ENV='{settings.APP_ENV}': {e}")
            logger.warning(f"Failed to connect to Supabase ({e}). Falling back to local In-Memory DB (APP_ENV='dev').")
            return InMemoryDatabase()

db = init_db()
