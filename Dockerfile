FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY dashboard ./dashboard
COPY config ./config
COPY main.py .

ENV PYTHONPATH=/app/src

# executo na porta informada pelo cloud run ou padrao 8000
CMD ["sh", "-c", "uvicorn dataops_ai.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
