# Dockerfile for OpenAI Proxy on Fly.io
# Build from repo root: fly deploy --config examples/openai_proxy/fly.toml

FROM python:3.11-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir build

COPY pyproject.toml README.md ./
COPY yamlgraph/ ./yamlgraph/
COPY examples/openai_proxy/ ./examples/openai_proxy/

RUN python -m build --wheel

# --- Runtime stage ---
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && \
    pip install --no-cache-dir uvicorn[standard] fastapi python-dotenv

COPY examples/openai_proxy/ ./examples/openai_proxy/

ENV PORT=8000
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

CMD ["python", "-m", "uvicorn", "examples.openai_proxy.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
