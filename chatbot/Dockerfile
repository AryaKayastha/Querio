FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.runtime.txt .
RUN pip install --no-cache-dir -r requirements.runtime.txt

COPY src/ ./src/
COPY vectorstore/ ./vectorstore/

CMD ["sh", "-c", "uvicorn querio_chatbot.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
