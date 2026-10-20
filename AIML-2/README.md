# 🎓 EduSense AI — AIML-2: Handwritten OCR & Question Segmentation

> **Module Responsibility:** AIML-2 (Handwritten OCR, Question Segmentation, Confidence Estimation, needsReview Flag, and `/transcribe` API).  
> **Core Question Answered:** *"What did the student write, and for which question?"*  
> **Guiding Principle:** *"AI assists. Teachers decide."* (No marks awarded by AI; final grading remains strictly teacher-controlled).

---

## 📁 1. Module Structure

```text
AIML-2/
│
├── ocr.py               # TrOCR text recognition (loads model, RGB, processes, generates, decodes)
├── segmentation.py      # Question segmentation (regex for Q1, Q2, Q 1, Q-1, Ans 1, 1., etc.)
├── confidence.py        # Token softmax probability confidence & needsReview thresholding
├── pipeline.py          # End-to-end transcription pipeline returning standardized JSON
├── api.py               # FastAPI microservice exposing POST /transcribe with temporary file cleanup
├── test.py              # Test suite for clean, difficult, multi-question, blank answers & API format
├── requirements.txt     # Python dependencies (torch, transformers, Pillow, opencv, fastapi, etc.)
│
└── sample/
    └── answer_sheet.jpg # Sample multi-question answer sheet image for testing
```

---

## 🎯 2. Project Boundaries (Strict AIML-2 Scope)

| Feature | Handled by AIML-2? | Handled by Teammates |
| :--- | :---: | :--- |
| Image Deskewing & Contrast Adjustment | ❌ | **AIML-1** (Image Preprocessing) |
| **Handwritten Text Recognition (OCR)** | ✅ | **AIML-2** (This Module) |
| **Question-wise Segmentation (Q1, Q2...)** | ✅ | **AIML-2** (This Module) |
| **OCR Confidence Calculation** | ✅ | **AIML-2** (This Module) |
| **needsReview Quality Flag** | ✅ | **AIML-2** (This Module) |
| **Transcription API (`/transcribe`)** | ✅ | **AIML-2** (This Module) |
| Semantic Evaluation & Concept Match | ❌ | **AIML-3** (Semantic Evaluation) |
| RAG Knowledge Base Retrieval | ❌ | **AIML-3** (Semantic Evaluation) |
| Suggested Marks Range Calculation | ❌ | **AIML-3** (Semantic Evaluation) |
| Final Marks Awarding | ❌ | **Teacher Final Decision** |

---

## 🧠 3. How the OCR Works (`ocr.py`)

Primary Model: **`microsoft/trocr-base-handwritten`**  
Architecture: **Vision Transformer (ViT) Encoder + RoBERTa Text Decoder**

### Step-by-Step Execution:
1. **Load Processor:** `TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")`
2. **Load Model:** `VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")`
3. **Open Image:** Opens file/bytes via PIL.
4. **Convert to RGB:** `.convert("RGB")` ensures consistent 3-channel input.
5. **Process Image:** Processor normalizes and transforms the image into visual patch tensors (`pixel_values`).
6. **Generate Tokens:** `model.generate(pixel_values, return_dict_in_generate=True, output_scores=True)`
7. **Decode Tokens:** `processor.batch_decode(outputs.sequences, skip_special_tokens=True)` converts token IDs to readable English text.
8. **Line Slicing for Full Pages:** Uses OpenCV horizontal projection profiling to detect and crop individual line strips, feeding them to TrOCR sequentially.

---

## ✂️ 4. How Question Segmentation Works (`segmentation.py`)

Detects question headers at the start of lines using regular expressions:
```python
QUESTION_MARKER_REGEX = re.compile(
    r'^(?:(?:q|question|ans|answer|\#)\s*[\.\-]?\s*(\d+)[\.\:\)\-]?|(\d+)[\.\:\)])\s*',
    re.IGNORECASE
)
```

### Supported Marker Variations:
- `Q1`, `Q2`, `Q3`
- `Q 1`, `Q 2`
- `Q-1`, `Q-2`
- `Q.1`, `Q.2`
- `q1`, `q 2`
- `Question 1:`, `Question 2.`
- `Ans 1:`, `Answer 2`
- `1.`, `1)`, `1:`

### Blank Answer Handling:
If a student leaves a question blank (e.g. wrote only `Q2` with no answer content), the pipeline produces:
```json
{
    "questionNumber": "Q2",
    "text": "",
    "confidence": 0.0,
    "needsReview": true
}
```
The pipeline never crashes on blank answers.

---

## 📊 5. How Confidence & needsReview Work (`confidence.py`)

### Token-level Softmax Confidence:
Instead of arbitrary heuristics, confidence is derived directly from the model's generation logits:
$$\text{Probability}_t = \max(\text{softmax}(\text{Logits}_t))$$
$$\text{Confidence}_{\text{line}} = \frac{1}{T} \sum_{t=1}^{T} \text{Probability}_t$$

Per-question confidence is the arithmetic mean of all lines belonging to that question.

### `needsReview` Flag Logic:
A question answer is flagged for teacher review (`needsReview = true`) if:
1. `confidence < threshold` (configurable, default: `0.70`).
2. `text == ""` (blank answer).
3. `len(text) < 3` (suspiciously short or corrupted text).

> **Important Note:** This confidence is a statistical estimate of OCR handwriting legibility, **not** an assessment of whether the student's answer is correct.

---

## 💻 6. Installation & Execution

### 1. Install Dependencies:
```bash
pip install -r requirements.txt
```

### 2. Run the Verification Tests:
```bash
python test.py
# or using pytest:
pytest test.py -v
```

### 3. Start the FastAPI Microservice:
```bash
uvicorn api:app --reload --port 8000
```
Open interactive Swagger documentation in your browser:  
👉 **`http://127.0.0.1:8000/docs`**

---

## 📡 7. API Request & Response Example

### Endpoint:
`POST /transcribe?answerSheetId=AS001&threshold=0.70`

### cURL Request:
```bash
curl -X POST "http://127.0.0.1:8000/transcribe?answerSheetId=AS001&threshold=0.70" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@sample/answer_sheet.jpg"
```

### JSON Response:
```json
{
    "answerSheetId": "AS001",
    "answers": [
        {
            "questionNumber": "Q1",
            "text": "Explain deadlock. Deadlock occurs when processes wait for resources held by each other.",
            "confidence": 0.94,
            "needsReview": false
        },
        {
            "questionNumber": "Q2",
            "text": "What is a process? A process is a program in execution.",
            "confidence": 0.88,
            "needsReview": false
        },
        {
            "questionNumber": "Q3",
            "text": "Explain semaphore. Semaphore is used for synchronization.",
            "confidence": 0.52,
            "needsReview": true
        }
    ]
}
```

---

## ⚠️ 8. Current Limitations & Assumptions

1. **Multi-Column Layouts:** The current line-segmentation algorithm uses horizontal projection profiling, which assumes single-column answer sheets. Complex two-column or interleaved layouts should be pre-segmented by AIML-1 into column bounding boxes.
2. **Cursive Overlaps:** Severely touching ascenders/descenders across lines can occasionally merge into one line crop; AIML-1's deskewing and binarization significantly improves separation.
3. **Execution Time on CPU:** Running Vision Transformer + RoBERTa on CPU takes 2–4 seconds per line. On an NVIDIA GPU (CUDA), inference executes in < 100ms.
