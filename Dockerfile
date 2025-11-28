# =========== STAGE 1: BUILDER ===========
FROM --platform=linux/amd64 python:3.11-slim as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    pkg-config \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


# =========== STAGE 2: FINAL RUNNER ===========
FROM --platform=linux/amd64 python:3.11-slim

# Create a non-root user
RUN addgroup --system app && adduser --system --group app

WORKDIR /home/app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    netcat-openbsd \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache /wheels/*

COPY . .

# Adjust permissions
RUN chown -R app:app /home/app

USER app

# Expose port
EXPOSE 8000

CMD ["sh", "-c", "daphne -b 0.0.0.0 -p $PORT core.asgi:application"]
