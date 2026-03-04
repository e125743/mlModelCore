FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

# YOLOモデルをbuild時にダウンロード
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

ENV PORT=8080
COPY . .
CMD ["python", "main.py"]