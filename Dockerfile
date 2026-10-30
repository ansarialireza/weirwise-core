FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 10001 weirwise && \
    useradd -u 10001 -g weirwise -m -s /bin/bash weirwise

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

COPY . .

RUN mkdir -p /app/var/data/storage /app/var/databases /app/data/storage && \
    chown -R weirwise:weirwise /app

USER weirwise

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

CMD ["uvicorn", "server.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
