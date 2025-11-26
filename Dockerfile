# =========== STAGE 1: BUILDER ===========
FROM python:3.11-slim as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


# =========== STAGE 2: FINAL RUNNER ===========
FROM python:3.11-slim

# Create a non-root user for security
RUN addgroup --system app && adduser --system --group app

WORKDIR /home/app

# Install runtime dependencies (libpq is needed for postgres)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install dependencies
RUN pip install --no-cache /wheels/*

# Copy project code
COPY . .

# Adjust permissions
RUN chown -R app:app /home/app

# Switch to non-root user
USER app

# Expose the port
EXPOSE 8000

# Start the application using Daphne ASGI server
CMD daphne -b 0.0.0.0 -p $PORT core.asgi:application