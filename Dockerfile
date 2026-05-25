FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN addgroup --system appuser && adduser --system --no-create-home --ingroup appuser appuser

RUN chown -R appuser:appuser /app

USER appuser

RUN mkdir -p /app/storage

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
