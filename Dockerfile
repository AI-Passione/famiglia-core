# Stage 1: Build Frontend (Node)
FROM node:18-alpine AS frontend-builder
WORKDIR /app
COPY src/famiglia_core/command_center/frontend/package*.json ./
RUN npm install
COPY src/famiglia_core/command_center/frontend/ .
ARG VITE_BACKEND_BASE
ARG VITE_API_BASE
ENV VITE_BACKEND_BASE=${VITE_BACKEND_BASE}
ENV VITE_API_BASE=${VITE_API_BASE}
RUN npm run build

# Stage 2: Final Production Image (Python + Nginx)
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT="/venv" \
    PATH="/venv/bin:$PATH" \
    PYTHONPATH="/app/src"

# Install system dependencies + Nginx
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    ca-certificates \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files first for caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --no-install-project --no-dev --no-cache

# Copy the rest of the application
COPY . .

# Copy Frontend build from Stage 1
COPY --from=frontend-builder /app/dist /usr/share/nginx/html

# Set up the entrypoint script
RUN chmod +x entrypoint.sh

# Expose ports for both Nginx (80) and API (8000)
EXPOSE 80 8000

# Run everything via entrypoint
CMD ["./entrypoint.sh"]
