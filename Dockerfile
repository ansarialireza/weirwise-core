FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

COPY . .

RUN mkdir -p /app/data/storage

EXPOSE 8000

CMD ["uvicorn", "server.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
