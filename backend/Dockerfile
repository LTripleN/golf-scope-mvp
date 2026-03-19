FROM python:3.11-slim-bookworm

# System deps needed by MediaPipe (OpenGL ES) and video processing (ffmpeg)
# On Debian Bookworm: libgl1-mesa-glx was replaced by libgl1
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgles2 \
    libgl1 \
    libegl1 \
    ffmpeg \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Render sets PORT env var; default to 10000
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}
