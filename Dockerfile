# Use official Python image as a base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files first for caching
# (Note: Assumes pyproject.toml or requirements.txt will exist eventually)
# COPY pyproject.toml .
# RUN uv sync --no-dev

# Copy the rest of the application
COPY . .

# Default command (placeholder)
CMD ["python", "-m", "famiglia_core"]
