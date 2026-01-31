#!/bin/bash
# Entrypoint script that waits for dependencies before starting the app

set -e

# Default values
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"
MAX_WAIT="${MAX_WAIT:-60}"

echo "🚀 Starting AI Marketing Content System..."
echo "📊 Waiting for dependencies..."

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
            exit 1
        fi
        sleep 1
        waited=$((waited + 1))
    done
    
    echo "✅ $service_name is ready"
}

# Wait for PostgreSQL
wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL"

# Wait for Redis
wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis"

echo "✅ All dependencies ready!"
echo "🌐 Starting uvicorn server..."

# Start the application
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8080 "$@"
