# Use a slim Python image
FROM python:3.11-slim

# Install system dependencies for psycopg2 and uv
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Set uv environment to avoid masking by host volumes
ENV UV_PROJECT_ENVIRONMENT="/venv"

# Copy the entire project to allow importing from src
COPY . .

RUN uv sync --no-dev --no-cache --frozen

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Run the API
CMD ["python", "src/command_center/backend/main.py"]
