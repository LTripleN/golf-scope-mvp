#!/usr/bin/env bash
# Render build script — installs system deps + Python packages

set -o errexit

# System libraries needed by MediaPipe (OpenGL ES) and OpenCV
apt-get update && apt-get install -y --no-install-recommends \
  libgles2-mesa \
  libgl1-mesa-glx \
  libegl1-mesa \
  ffmpeg \
  && rm -rf /var/lib/apt/lists/*

pip install --upgrade pip
pip install -r requirements.txt
