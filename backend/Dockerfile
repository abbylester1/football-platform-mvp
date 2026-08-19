FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 tesseract-ocr curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Pre-download YOLO models (detection + pose) to avoid cold-start latency
RUN python -c "from ultralytics import YOLO; YOLO('yolo11s.pt'); YOLO('yolo11s-pose.pt')"
ENV STORAGE_DIR=/data
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
