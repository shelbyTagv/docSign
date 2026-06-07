FROM python:3.11-slim

# Create a non-root user for security — running as root inside containers
# is a significant attack surface if the container is compromised
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install system dependencies needed for Pillow, cryptography, and mysqlclient
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    default-libmysqlclient-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first — Docker layer caching means we only reinstall
# dependencies when requirements.txt actually changes, not on every code change
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for RSA key storage and ensure appuser owns them
RUN mkdir -p /app/keys && chown -R appuser:appuser /app

USER appuser

EXPOSE 8001

# Run Alembic migrations before starting the server.
# Using a shell script so we can run multiple commands in sequence.
CMD ["sh", "-c", "python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8001"]
