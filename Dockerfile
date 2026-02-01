# ============================================
# MULTI-STAGE BUILD FOR AI MARKETING SYSTEM
# Optimized for smaller image size & faster startup
# ============================================

# ============================================
# STAGE 1: Python Dependencies Builder
# ============================================
FROM python:3.11-slim AS python-builder

WORKDIR /build

# Install build dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install production dependencies only
COPY requirements-prod.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements-prod.txt

# ============================================
# STAGE 2: Frontend Builder (Next.js Static Export)
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /build

# Copy package files first for better caching
COPY src/dashboard/package*.json ./

# Install all dependencies (including devDependencies for build)
RUN npm ci

# Copy source and build (output: 'export' generates 'out/' directory)
COPY src/dashboard/ ./
RUN npm run build

# ============================================
# STAGE 3: Production Runtime (Minimal)
# ============================================
FROM python:3.11-slim AS production

WORKDIR /app

# Install only essential runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=python-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy ONLY the static export from frontend builder (out/ directory)
# No node_modules needed - it's a static site!
COPY --from=frontend-builder /build/out /app/src/dashboard/out

# Copy application source code
COPY src/ /app/src/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/

# Copy static admin directory
COPY static/ /app/static/

# Copy entrypoint script
COPY scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Health check with appropriate timing
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD curl -f "http://localhost:${PORT:-8080}/health" || exit 1

# Use entrypoint script that waits for dependencies
ENTRYPOINT ["/app/entrypoint.sh"]
