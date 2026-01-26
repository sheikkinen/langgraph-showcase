# Dockerfile for Booking API on Fly.io
# Multi-stage build for smaller image

FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir build

# Copy package files
COPY pyproject.toml README.md ./
COPY yamlgraph/ ./yamlgraph/
COPY examples/booking/ ./examples/booking/
COPY graphs/ ./graphs/
COPY prompts/ ./prompts/

# Build wheel
RUN python -m build --wheel

# --- Runtime stage ---
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && pip install --no-cache-dir redis orjson httpx uvicorn[standard] fastapi

# Copy application code
COPY examples/booking/ ./examples/booking/
COPY graphs/ ./graphs/
COPY prompts/ ./prompts/

# Create data directory for SQLite volume
RUN mkdir -p /data

# Set environment
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

# Run app
CMD ["python", "-m", "uvicorn", "examples.booking.main:app", "--host", "0.0.0.0", "--port", "8000"]
