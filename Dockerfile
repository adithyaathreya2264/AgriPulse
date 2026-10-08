FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# ffmpeg: voice notes (webm/ogg -> wav); curl: kept for the HTTP calls that still use it
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# the trained price forecast model (read at run time, no network call)
COPY ml ./ml

EXPOSE 10000

# Render sets $PORT; 10000 is its default
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
