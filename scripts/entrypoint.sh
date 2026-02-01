#!/bin/bash
# Entrypoint script that waits for dependencies before starting the app

set -e

# Default values
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"
MAX_WAIT="${MAX_WAIT:-60}"
SKIP_WAIT="${SKIP_WAIT:-false}"

# Auto-detect from DATABASE_URL if DB_HOST is default
if [ -n "$DATABASE_URL" ] && [ "$DB_HOST" = "db" ]; then
    echo "🔍 Detecting DB connection from DATABASE_URL..."
    # Use python to parse safely reading from env var to avoid shell injection
    DB_HOST=$(python -c "import os, urllib.parse; print(urllib.parse.urlparse(os.environ.get('DATABASE_URL')).hostname or 'db')")
    DB_PORT=$(python -c "import os, urllib.parse; print(urllib.parse.urlparse(os.environ.get('DATABASE_URL')).port or 5432)")
fi

# Auto-detect from REDIS_URL if REDIS_HOST is default
if [ -n "$REDIS_URL" ] && [ "$REDIS_HOST" = "redis" ]; then
    echo "🔍 Detecting Redis connection from REDIS_URL..."
    REDIS_HOST=$(python -c "import os, urllib.parse; print(urllib.parse.urlparse(os.environ.get('REDIS_URL')).hostname or 'redis')")
    REDIS_PORT=$(python -c "import os, urllib.parse; print(urllib.parse.urlparse(os.environ.get('REDIS_URL')).port or 6379)")
fi

echo "🚀 Starting AI Marketing Content System..."

# Auto-detect Zeabur environment and skip wait if using managed services
if [ -n "$ZEABUR" ] || [ -n "$ZEABUR_SERVICE_ID" ]; then
    echo "🔵 Zeabur environment detected"
    # If using Zeabur managed database/redis, skip wait
    if [[ "$DATABASE_URL" == *"zeabur"* ]] || [[ "$REDIS_URL" == *"zeabur"* ]]; then
        echo "📦 Using Zeabur managed services, skipping dependency wait"
        SKIP_WAIT="true"
    fi
fi

echo "📊 Checking dependencies..."

# Function to wait for a service
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local waited=0
    
    echo "⏳ Waiting for $service_name ($host:$port)..."
    
    while ! nc -z "$host" "$port" 2>/dev/null; do
        if [ $waited -ge $MAX_WAIT ]; then
            echo "❌ Timeout waiting for $service_name after ${MAX_WAIT}s"
            echo "   (Skipping wait constraint to allow partial startup if possible...)"
            break
            # We break instead of exit, to allow the app to try connecting (it might fail more gracefully or handle it)
        fi
        sleep 1
        waited=$((waited + 1))
    done
    
    if [ $waited -lt $MAX_WAIT ]; then
        echo "✅ $service_name is ready"
    fi
}

# Skip dependency wait if SKIP_WAIT is set (useful for managed services like Zeabur)
if [ "$SKIP_WAIT" = "true" ]; then
    echo "⏭️  Skipping dependency wait (SKIP_WAIT=true)"
else
    # Wait for PostgreSQL
    wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL"

    # Wait for Redis
    wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis"
fi

echo "✅ Dependency checks completed."
echo "🌐 Starting uvicorn server..."

# Start the application with dynamic port
PORT="${PORT:-8080}"
exec uvicorn src.api.main:app --host 0.0.0.0 --port "$PORT" "$@"
