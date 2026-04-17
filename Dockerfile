FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py .
COPY i18n.py .
COPY llm_client.py .
COPY failure_tracker.py .
COPY telegram.py .
COPY guardian.py .
COPY locales/ locales/

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--preload", "--max-requests", "1000", "--max-requests-jitter", "100", "--timeout", "120", "guardian:app"]
