FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install --with-deps chromium

COPY . .

RUN mkdir -p /app/data

CMD ["sh", "-c", "uvicorn api:app --host ${APP_HOST:-0.0.0.0} --port ${PORT:-8000}"]
