FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN apt-get update && apt-get install -y --no-install-recommends wget ca-certificates && \
    wget -q https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.onnx -O /app/yolo11n.onnx && \
    rm -rf /var/lib/apt/lists/*
ENV STORAGE_DIR=/data YOLO_MODEL=/app/yolo11n.onnx
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
