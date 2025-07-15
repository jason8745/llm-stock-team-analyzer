# Use Python 3.12 slim image as base (latest for security updates)
FROM python:3.12-slim-bookworm

# Update system packages to address vulnerabilities
RUN apt-get update && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev dependencies for production)
RUN uv sync --frozen --no-cache --no-dev

# Copy source code
COPY . .

# Set Python path to include the project root
ENV PYTHONPATH=/app

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash analyzer && \
    chown -R analyzer:analyzer /app
USER analyzer

# Run the main CLI application
CMD ["uv", "run", "python", "main.py"]