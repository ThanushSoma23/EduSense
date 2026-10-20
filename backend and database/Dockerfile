# EduSense AI Backend — Production Dockerfile
# Optimized for CPU inference, baked OCR model weights, and zero-download container startup.

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    EASYOCR_DOWNLOAD_ENABLED=false \
    STORAGE_BACKEND=local \
    STORAGE_LOCAL_DIR=uploads

# Install system dependencies required for OpenCV, PyTorch CPU, and PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Install CPU-only PyTorch and torchvision first to avoid heavy CUDA packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 2. Install application dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Bake EasyOCR English detection and recognition models into the image at build time
# Uses pre-cached craft_mlt_25k.pth and english_g2.pth
RUN mkdir -p /root/.EasyOCR/model
COPY .EasyOCR_model/* /root/.EasyOCR/model/
RUN python -c "import easyocr; reader = easyocr.Reader(['en'], gpu=False, download_enabled=False); print('EasyOCR offline weight verification complete.')" \
    && test -f /root/.EasyOCR/model/craft_mlt_25k.pth \
    && test -f /root/.EasyOCR/model/english_g2.pth

# 4. Copy backend application source code
COPY . /app/

# Create uploads directory structure
RUN mkdir -p /app/uploads/submissions /app/uploads/questions /app/uploads/references

# Expose FastAPI default port
EXPOSE 8000

# Health check using the backend health endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default runtime command: starts single Uvicorn worker to optimize memory and eliminate duplicate OCR model caching
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
