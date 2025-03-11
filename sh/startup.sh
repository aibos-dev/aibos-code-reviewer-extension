#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

echo "Starting the application..."

# Wait for database to be ready
echo "Waiting for PostgreSQL..."
MAX_DB_RETRIES=30
DB_RETRY_COUNT=0

while [ $DB_RETRY_COUNT -lt $MAX_DB_RETRIES ]; do
    if nc -z postgres 5432; then
        echo "PostgreSQL is available"
        break
    fi
    DB_RETRY_COUNT=$((DB_RETRY_COUNT+1))
    echo "Waiting for PostgreSQL... attempt $DB_RETRY_COUNT/$MAX_DB_RETRIES"
    sleep 2
done

# Check if PostgreSQL is running
if [ $DB_RETRY_COUNT -eq $MAX_DB_RETRIES ]; then
    echo "ERROR: PostgreSQL not responding after $MAX_DB_RETRIES attempts"
    exit 1
fi

# Run database migrations
echo "Running database migrations..."
python -c "
from src.database import engine
from src.models_db import Base
print('Creating database tables if they do not exist...')
Base.metadata.create_all(bind=engine)
print('Database setup completed!')
"

# Try to connect to Ollama but don't fail if it's not available
echo "Checking if Ollama service is available..."
if curl -s --connect-timeout 5 http://ollama:11434/ > /dev/null; then
    echo "Ollama is running"
    
    # If OLLAMA_MODEL is defined, check if it's available
    if [ -n "$OLLAMA_MODEL" ]; then
        echo "Checking if model $OLLAMA_MODEL is available..."
        if curl -s http://ollama:11434/api/tags | grep -q "$OLLAMA_MODEL"; then
            echo "Model $OLLAMA_MODEL is available"
        else
            echo "Model $OLLAMA_MODEL is not available. The API will continue but LLM features may not work."
        fi
    fi
else
    echo "Ollama service is not available. The API will continue but LLM features may not work."
fi

# Run the API server
echo "Starting API server..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000