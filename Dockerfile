FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Application source (needed by hatchling to build the wheel)
COPY pyproject.toml README.md ./
COPY src/ src/

# Python dependencies + package
RUN pip install --no-cache-dir .
COPY data/ data/

# Ensure runtime data directories exist
RUN mkdir -p data/uploads data/cache

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "estym_ai.main:app", "--host", "0.0.0.0", "--port", "8000"]
