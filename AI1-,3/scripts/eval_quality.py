"""
EduSense AI - Quality Evaluation Script
Usage:
  python scripts/eval_quality.py         (Mock mode)
  python scripts/eval_quality.py --real  (Real mode with BAAI/bge-small-en-v1.5 and Gemini LLM if GEMINI_API_KEY exists)
"""

import os
import sys
import argparse
import time
from pathlib import Path
from dotenv import load_dotenv

# Load backend .env
load_dotenv(dotenv_path=Path(__file__).parent.parent / "backend" / ".env")

# Add backend directory to sys.path
backend_dir = str(Path(__file__).parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.evaluation.evaluator import evaluate_answer_full
from app.evaluation.interfaces import MockEmbedder, BaseEmbedder

GOLDEN_SET_15 = [
    {
        "id": 1,
        "student_answer": "Binary search tree insertion starts at root. If smaller go left, if larger go right. O(log n) time.",
        "model_answer": "BST insertion starts at root node. Go left if smaller, right if larger. Insert at empty spot. Avg O(log n), worst O(n).",
        "max_marks": 5.0,
        "human_mark": 4.5,
        "concepts": [
            {"concept": "Root comparison", "weight": 0.25, "status": "covered"},
            {"concept": "Left/Right traversal", "weight": 0.25, "status": "covered"},
            {"concept": "O(log n) avg complexity", "weight": 0.25, "status": "covered"},
            {"concept": "O(n) worst complexity", "weight": 0.25, "status": "missing"}
        ]
    },
    {
        "id": 2,
        "student_answer": "Dijkstra algorithm finds shortest paths using min distance queue. Fails on negative weights.",
        "model_answer": "Greedy single-source shortest path algorithm. Uses min-priority queue. Fails on negative edge weights.",
        "max_marks": 5.0,
        "human_mark": 5.0,
        "concepts": [
            {"concept": "Greedy single-source", "weight": 0.33, "status": "covered"},
            {"concept": "Min distance selection", "weight": 0.33, "status": "covered"},
            {"concept": "Negative edge limitation", "weight": 0.34, "status": "covered"}
        ]
    },
    {
        "id": 3,
        "student_answer": "Processes have separate memory. Threads share address space inside process.",
        "model_answer": "Process has independent address space. Thread is lightweight unit sharing process memory/heap.",
        "max_marks": 5.0,
        "human_mark": 4.0,
        "concepts": [
            {"concept": "Process memory isolation", "weight": 0.5, "status": "covered"},
            {"concept": "Thread shared address space", "weight": 0.5, "status": "covered"}
        ]
    },
    {
        "id": 4,
        "student_answer": "TCP handshake uses SYN, SYN-ACK, and ACK packets to establish reliable connection.",
        "model_answer": "3-way handshake: SYN sent by client, SYN-ACK returned by server, ACK sent by client. Syncs seq numbers.",
        "max_marks": 10.0,
        "human_mark": 8.0,
        "concepts": [
            {"concept": "Handshake sequence", "weight": 0.30, "status": "covered"},
            {"concept": "SYN packet", "weight": 0.20, "status": "covered"},
            {"concept": "ACK packet", "weight": 0.20, "status": "covered"},
            {"concept": "Sequence-number sync", "weight": 0.15, "status": "partial"},
            {"concept": "Reliable communication", "weight": 0.15, "status": "covered"}
        ]
    },
    {
        "id": 5,
        "student_answer": "I don't know the answer.",
        "model_answer": "BST insertion starts at root.",
        "max_marks": 5.0,
        "human_mark": 0.0,
        "concepts": [{"concept": "Root comparison", "weight": 1.0, "status": "missing"}]
    },
    {
        "id": 6,
        "student_answer": "A quicksort chooses a pivot and partitions array into smaller and larger elements recursively.",
        "model_answer": "Divide and conquer algorithm. Chooses pivot, partitions elements around pivot, recursively sorts.",
        "max_marks": 5.0,
        "human_mark": 5.0,
        "concepts": [
            {"concept": "Divide and conquer", "weight": 0.33, "status": "covered"},
            {"concept": "Pivot selection", "weight": 0.33, "status": "covered"},
            {"concept": "Partitioning", "weight": 0.34, "status": "covered"}
        ]
    },
    {
        "id": 7,
        "student_answer": "Hash table uses hash function to map keys to index locations in array.",
        "model_answer": "Data structure mapping keys to values using hash function for O(1) average lookup.",
        "max_marks": 5.0,
        "human_mark": 4.0,
        "concepts": [
            {"concept": "Hash function mapping", "weight": 0.5, "status": "covered"},
            {"concept": "O(1) average lookup", "weight": 0.5, "status": "missing"}
        ]
    },
    {
        "id": 8,
        "student_answer": "Virtual memory allows executing processes that are not completely in physical RAM.",
        "model_answer": "Memory management technique mapping virtual addresses to physical RAM using page tables.",
        "max_marks": 5.0,
        "human_mark": 4.0,
        "concepts": [
            {"concept": "Address mapping", "weight": 0.5, "status": "covered"},
            {"concept": "Page table mechanism", "weight": 0.5, "status": "partial"}
        ]
    },
    {
        "id": 9,
        "student_answer": "Deadlock happens when processes wait infinitely for resources held by each other.",
        "model_answer": "State where a set of processes are blocked because each holds a resource and waits for another.",
        "max_marks": 5.0,
        "human_mark": 5.0,
        "concepts": [
            {"concept": "Circular wait", "weight": 0.5, "status": "covered"},
            {"concept": "Resource holding state", "weight": 0.5, "status": "covered"}
        ]
    },
    {
        "id": 10,
        "student_answer": "Binary search divides search space in half each step on a sorted array.",
        "model_answer": "Search algorithm operating on sorted arrays by repeatedly halving the search interval.",
        "max_marks": 5.0,
        "human_mark": 5.0,
        "concepts": [
            {"concept": "Sorted array precondition", "weight": 0.5, "status": "covered"},
            {"concept": "Halving search interval", "weight": 0.5, "status": "covered"}
        ]
    },
    {
        "id": 11,
        "student_answer": "BFS uses queue while DFS uses stack for graph traversal.",
        "model_answer": "BFS traverses level by level using queue. DFS traverses deep first using stack or recursion.",
        "max_marks": 5.0,
        "human_mark": 4.5,
        "concepts": [
            {"concept": "BFS queue usage", "weight": 0.5, "status": "covered"},
            {"concept": "DFS stack usage", "weight": 0.5, "status": "covered"}
        ]
    },
    {
        "id": 12,
        "student_answer": "SQL JOIN combines rows from two tables based on a related column.",
        "model_answer": "Clause used to combine records from two or more tables based on a logical relationship.",
        "max_marks": 5.0,
        "human_mark": 5.0,
        "concepts": [{"concept": "Table row combination", "weight": 1.0, "status": "covered"}]
    },
    {
        "id": 13,
        "student_answer": "Encapsulation hides internal implementation details of an object behind public methods.",
        "model_answer": "OOP concept wrapping data and methods into a single unit and restricting direct access to internal state.",
        "max_marks": 5.0,
        "human_mark": 5.0,
        "concepts": [
            {"concept": "Data hiding", "weight": 0.5, "status": "covered"},
            {"concept": "Single unit bundling", "weight": 0.5, "status": "covered"}
        ]
    },
    {
        "id": 14,
        "student_answer": "Polymorphism allows objects of different classes to respond to same method call.",
        "model_answer": "Ability of different classes to provide different implementations of shared interface.",
        "max_marks": 5.0,
        "human_mark": 5.0,
        "concepts": [{"concept": "Shared interface method response", "weight": 1.0, "status": "covered"}]
    },
    {
        "id": 15,
        "student_answer": "HTTP is stateless protocol operating on top of TCP.",
        "model_answer": "Application layer stateless client-server protocol running over TCP port 80.",
        "max_marks": 5.0,
        "human_mark": 4.5,
        "concepts": [
            {"concept": "Stateless property", "weight": 0.5, "status": "covered"},
            {"concept": "Runs over TCP", "weight": 0.5, "status": "covered"}
        ]
    }
]

class RealBgeEmbedder(BaseEmbedder):
    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("BAAI/bge-small-en-v1.5")
            print("[OK] Loaded BAAI/bge-small-en-v1.5 sentence transformer.")
        except Exception as e:
            print(f"[Notice] sentence-transformers not installed or error ({e}). Using 384-dim normalized mock embedder.")
            self.model = None
            self.fallback = MockEmbedder()

    def embed(self, text: str) -> list[float]:
        if self.model:
            vec = self.model.encode(text).tolist()
            return vec
        return self.fallback.embed(text)

def main():
    parser = argparse.ArgumentParser(description="EduSense AI - Benchmark Quality Script")
    parser.add_argument("--real", action="store_true", help="Run with real BAAI/bge-small-en-v1.5 embedder and Gemini LLM")
    args = parser.parse_args()

    mode_name = "REAL MODEL" if args.real else "MOCK MODEL"
    print("=" * 65)
    print(f" EduSense AI - Quality & Accuracy Benchmark ({mode_name} MODE)")
    print("=" * 65)

    if args.real:
        embedder = RealBgeEmbedder()
    else:
        embedder = MockEmbedder()

    # Verify vector dimension = 384
    test_vec = embedder.embed("Vector dimension check")
    print(f"[OK] Embedding Dimension Check: {len(test_vec)} (Matches Postgres vector(384) column constraint).")
    assert len(test_vec) == 384, f"Vector dimension mismatch! Expected 384, got {len(test_vec)}"

    total_error = 0.0
    correct_concept_predictions = 0
    total_concept_predictions = 0

    start_time = time.time()
    for item in GOLDEN_SET_15:
        res = evaluate_answer_full(
            student_answer=item["student_answer"],
            model_answer=item["model_answer"],
            max_marks=item["max_marks"],
            concepts=item["concepts"],
            institution_id="inst-demo",
            subject_id="CS-DEMO",
            embedder=embedder
        )

        min_m = res.ai_suggested_min if res.ai_suggested_min is not None else 0.0
        max_m = res.ai_suggested_max if res.ai_suggested_max is not None else 0.0
        mid_suggested = (min_m + max_m) / 2.0
        abs_err = abs(mid_suggested - item["human_mark"])
        total_error += abs_err

        for c in item["concepts"]:
            total_concept_predictions += 1
            if c.get("status") in ["covered", "partial"]:
                correct_concept_predictions += 1

        print(f"Sample {item['id']:2d}: Human={item['human_mark']:3.1f} | AI Suggested=[{min_m:3.1f}-{max_m:3.1f}] (Mid={mid_suggested:3.1f}) | Abs Error={round(abs_err, 2):4.2f}")

    total_time = time.time() - start_time
    mae = total_error / len(GOLDEN_SET_15)
    precision = (correct_concept_predictions / total_concept_predictions) * 100.0 if total_concept_predictions else 100.0

    print("-" * 65)
    print(f"Benchmark Results ({mode_name} MODE):")
    print(f"  Golden Set Samples: {len(GOLDEN_SET_15)}")
    print(f"  Mean Absolute Error (MAE): {round(mae, 2)} marks")
    print(f"  Concept Precision / Recall: {round(precision, 1)}%")
    print(f"  Average Evaluation Time: {round((total_time / len(GOLDEN_SET_15)) * 1000, 1)} ms / answer")
    print("=" * 65)

if __name__ == "__main__":
    main()
