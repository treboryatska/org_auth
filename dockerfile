# Dockerfile for Dagster project

# --- Builder Stage ---
    FROM python:3.13-slim AS builder

    # Install build-time dependencies, including curl and unzip for Bun
    RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        build-essential \
        nodejs \
        npm \
        curl \
        unzip \
        && rm -rf /var/lib/apt/lists/*
    
    # Install Bun
    RUN curl -fsSL https://bun.sh/install | bash
    ENV PATH="/root/.bun/bin:$PATH"
    
    WORKDIR /opt/dagster/app
    
    # Install uv and Python packages
    RUN pip install uv
    COPY requirements.txt .
    RUN uv pip install --system --no-cache -r requirements.txt
    
    # Copy application code from the subfolder, preserving the parent directory
    COPY dagster_project/ ./dagster_project/
    
    # Copy package manifests for dependency installation
    COPY dagster_project/hypergraph/package*.json ./dagster_project/hypergraph/
    
    # Use Bun to install dependencies (faster than npm ci)
    RUN cd dagster_project/hypergraph && bun install --frozen-lockfile
    
    # Use Bun to build the TypeScript code
    # This command looks at package.json and runs the "build" script
    RUN cd dagster_project/hypergraph && bun run build
    
    # Create DAGSTER_HOME and copy the instance config
    RUN mkdir -p /opt/dagster/dagster_home
    COPY dagster.yaml /opt/dagster/dagster_home/
    COPY workspace.yaml /opt/dagster/dagster_home/
    
    # --- Final Stage ---
    FROM python:3.13-slim

    # Set the Zig version to install
    ENV ZIG_VERSION=0.14.0
    
# Install runtime dependencies and manually install Zig
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Dependencies for your app
    nodejs \
    npm \
    git \
    # Dependencies needed to download and extract Zig
    curl \
    xz-utils \
    && \
    # Detect architecture and set Zig arch string
    ARCH=$(dpkg --print-architecture) && \
    case "${ARCH}" in \
        amd64) ZIG_ARCH="x86_64";; \
        arm64) ZIG_ARCH="aarch64";; \
        *) echo "Unsupported architecture: ${ARCH}"; exit 1;; \
    esac && \
    # Download, extract, and install Zig
    curl -L "https://ziglang.org/download/${ZIG_VERSION}/zig-linux-${ZIG_ARCH}-${ZIG_VERSION}.tar.xz" -o zig.tar.xz && \
    tar -xf zig.tar.xz -C /usr/local --strip-components=1 && \
    # Create a symlink to make the 'zig' command available
    ln -s /usr/local/zig /usr/local/bin/zig && \
    # Clean up downloaded files and apt cache
    rm zig.tar.xz && \
    rm -rf /var/lib/apt/lists/*
    
    # Create a non-root user and group
    RUN groupadd --system app && useradd --system --gid app appuser
    
    WORKDIR /opt/dagster/app
    
    # Copy installed Python packages from the builder stage
    COPY --from=builder /usr/local/bin /usr/local/bin
    COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
    
    # Copy the application code (including the compiled JS in dist/) and dagster home
    COPY --from=builder --chown=appuser:app /opt/dagster /opt/dagster
    
    # Set environment variables
    ENV DAGSTER_HOME=/opt/dagster/dagster_home
    ENV PYTHONPATH=/opt/dagster/app
    # Point the Zig cache to a writable temporary directory
    ENV ZIG_GLOBAL_CACHE_DIR=/tmp/zig-cache
    
    # Switch to non-root user
    USER appuser
    
    # Expose Dagster webserver port
    EXPOSE 3000
    
    # Health check
    HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
        CMD curl -f http://localhost:3000/health || exit 1
    
    # Start Dagster webserver
    CMD ["dagster", "dev", "-w", "/opt/dagster/dagster_home/workspace.yaml", "--host", "0.0.0.0", "--port", "3000"]