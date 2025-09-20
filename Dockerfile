# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TZ=Asia/Kolkata \
    DOCKER_ENV=1

# Install system dependencies and clean up in one layer to reduce image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

# Create app directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies and clean up pip cache
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf ~/.cache/pip

# Copy application code
COPY src/ ./src/
COPY main.py .
COPY category_list_mapping.json .

# Note: config.yaml, client_secret.json, and token.pkl should be mounted as volumes
# These files contain sensitive data and should not be baked into the image

# Create directory for logs and data
RUN mkdir -p /app/logs /app/data

# Copy the entrypoint script
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# Create non-root user for security
RUN groupadd -r gtasks && useradd -r -g gtasks gtasks \
    && chown -R gtasks:gtasks /app
USER gtasks

# Health check to ensure the container is working
HEALTHCHECK --interval=5m --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["./docker-entrypoint.sh"]