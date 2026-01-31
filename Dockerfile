# ============================================
# MULTI-STAGE BUILD FOR AI MARKETING SYSTEM
# Optimized for smaller image size & faster startup
# ============================================

# ============================================
# STAGE 1: Python Dependencies Builder
# ============================================
FROM python:3.10-slim AS python-builder

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
# STAGE 2: Frontend Builder (Next.js Dashboard)
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /build

# Copy package files first for better caching
COPY src/dashboard/package*.json ./

# Install dependencies
RUN npm ci --only=production=false

# Copy source and build
COPY src/dashboard/ ./
RUN npm run build

# ============================================
# STAGE 3: Production Runtime
# ============================================
FROM python:3.10-slim AS production

WORKDIR /app

# Install only runtime dependencies (no gcc, no npm)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=python-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy built dashboard from frontend builder
COPY --from=frontend-builder /build/.next /app/src/dashboard/.next
COPY --from=frontend-builder /build/public /app/src/dashboard/public
COPY --from=frontend-builder /build/node_modules /app/src/dashboard/node_modules
COPY --from=frontend-builder /build/package.json /app/src/dashboard/package.json

# Copy application source code
COPY src/ /app/src/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application with optimized settings
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2", "--loop", "uvloop", "--http", "httptools"]
