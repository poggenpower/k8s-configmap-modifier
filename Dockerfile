FROM python:3.11-alpine

# Install system dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scripts directory
COPY scripts/ ./scripts/

# Create non-root user
RUN adduser -D -s /bin/sh appuser
USER appuser

# Set entrypoint
ENTRYPOINT ["/bin/sh"]
