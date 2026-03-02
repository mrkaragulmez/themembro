# backend/Dockerfile
# Faz 1 — FastAPI container

FROM python:3.12-slim

WORKDIR /app

# Sistem bağımlılıkları
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıkları (cache katmanı)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kaynak kod (dev'de volume mount ile override edilir)
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
