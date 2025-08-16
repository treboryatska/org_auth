# Dockerfile for Dagster project

# --- Builder Stage ---
FROM python:3.13-slim AS builder

# Install build-time dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/dagster/app

# Install uv and Python packages
RUN pip install uv
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application code
COPY . .

# Create DAGSTER_HOME and copy the instance config
RUN mkdir -p /opt/dagster/dagster_home
COPY dagster.yaml /opt/dagster/dagster_home/

COPY workspace.yaml /opt/dagster/dagster_home/

# --- Final Stage ---
FROM python:3.13-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and group
RUN groupadd --system app && useradd --system --gid app appuser

WORKDIR /opt/dagster/app

# Copy installed Python packages from the builder stage
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages

# Copy the application code and dagster home
COPY --from=builder --chown=appuser:app /opt/dagster /opt/dagster

# Set environment variables
ENV DAGSTER_HOME=/opt/dagster/dagster_home
ENV PYTHONPATH=/opt/dagster/app

# Switch to non-root user
USER appuser

# Expose Dagster webserver port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Start Dagster webserver
CMD ["dagster", "dev", "-w", "/opt/dagster/dagster_home/workspace.yaml", "--host", "0.0.0.0", "--port", "3000"]