FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HF_HOME=/root/.cache/huggingface
ENV TRANSFORMERS_CACHE=/root/.cache/huggingface
ENV TORCH_HOME=/root/.cache/torch

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        curl \
        ffmpeg \
        pkg-config \
        build-essential \
        python3-dev \
        libffi-dev \
        libssl-dev \
        libsndfile1 \
        libsndfile1-dev \
        libavcodec-dev \
        libavformat-dev \
        libavdevice-dev \
        libavutil-dev \
        libavfilter-dev \
        libswscale-dev \
        libswresample-dev \
        libopus-dev \
        libvpx-dev \
        libx264-dev \
        libx265-dev \
    && rm -rf /var/lib/apt/lists/*

COPY apps/sound_generation_service/requirements.txt /app/requirements.txt

RUN pip install --upgrade pip setuptools wheel Cython numpy \
    && pip install --no-cache-dir av==11.0.0 \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY apps/sound_generation_service/app /app/app

EXPOSE 8000