FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-ci-constraints.txt ./
# Optional combined CA bundle for proxy-backed cloud builds; never retained in layers.
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir --upgrade pip setuptools -c requirements-ci-constraints.txt && \
    pip install --no-cache-dir --no-deps --index-url https://download.pytorch.org/whl/cpu torch -c requirements-ci-constraints.txt && \
    pip install --no-cache-dir -r requirements.txt -c requirements-ci-constraints.txt

COPY . .

ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_CACHE_DIR=/app/models

RUN chmod +x /app/scripts/docker-entrypoint.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=5 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/health'); r.raise_for_status()" || exit 1

ENTRYPOINT ["sh", "/app/scripts/docker-entrypoint.sh"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
