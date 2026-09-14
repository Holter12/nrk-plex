FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir .

RUN mkdir -p /config /cache

EXPOSE 8080

CMD ["uvicorn", "nrk_plex.app:app", "--host", "0.0.0.0", "--port", "8080"]
