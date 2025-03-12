#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
fi

echo "Setting up project environment..."

# Set default values if not provided
: "${POSTGRES_HOST:=localhost}"
: "${POSTGRES_PORT:=5432}"
: "${REMOTE_POSTGRES_PORT:=5432}"

# Function to test PostgreSQL connection
test_postgres_connection() {
    local host=$1
    local port=$2
    local user=$3
    local password=$4
    local db=$5
    
    echo "Testing connection to PostgreSQL at ${host}:${port}..."
    
    # Use PGPASSWORD to avoid password prompt with psql
    PGPASSWORD="$password" psql -h "$host" -p "$port" -U "$user" -d "$db" -c "SELECT 1;" >/dev/null 2>&1
    return $?
}

# First try local PostgreSQL
DB_CONNECTED=false

if [ -n "$POSTGRES_HOST" ] && [ -n "$POSTGRES_USER" ] && [ -n "$POSTGRES_PASSWORD" ] && [ -n "$POSTGRES_DB" ]; then
    echo "Attempting to connect to local PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
    
    if test_postgres_connection "$POSTGRES_HOST" "$POSTGRES_PORT" "$POSTGRES_USER" "$POSTGRES_PASSWORD" "$POSTGRES_DB"; then
        echo "Successfully connected to local PostgreSQL"
        export ACTIVE_POSTGRES_HOST="$POSTGRES_HOST"
        export ACTIVE_POSTGRES_PORT="$POSTGRES_PORT"
        export ACTIVE_POSTGRES_USER="$POSTGRES_USER"
        export ACTIVE_POSTGRES_PASSWORD="$POSTGRES_PASSWORD"
        export ACTIVE_POSTGRES_DB="$POSTGRES_DB"
        DB_CONNECTED=true
    else
        echo "Failed to connect to local PostgreSQL"
    fi
fi

# If local connection failed, try remote
if [ "$DB_CONNECTED" = false ] && [ -n "$REMOTE_POSTGRES_HOST" ] && [ -n "$REMOTE_POSTGRES_USER" ] && [ -n "$REMOTE_POSTGRES_PASSWORD" ] && [ -n "$REMOTE_POSTGRES_DB" ]; then
    echo "Attempting to connect to remote PostgreSQL at ${REMOTE_POSTGRES_HOST}:${REMOTE_POSTGRES_PORT}..."
    
    if test_postgres_connection "$REMOTE_POSTGRES_HOST" "$REMOTE_POSTGRES_PORT" "$REMOTE_POSTGRES_USER" "$REMOTE_POSTGRES_PASSWORD" "$REMOTE_POSTGRES_DB"; then
        echo "Successfully connected to remote PostgreSQL"
        export ACTIVE_POSTGRES_HOST="$REMOTE_POSTGRES_HOST"
        export ACTIVE_POSTGRES_PORT="$REMOTE_POSTGRES_PORT"
        export ACTIVE_POSTGRES_USER="$REMOTE_POSTGRES_USER"
        export ACTIVE_POSTGRES_PASSWORD="$REMOTE_POSTGRES_PASSWORD"
        export ACTIVE_POSTGRES_DB="$REMOTE_POSTGRES_DB"
        DB_CONNECTED=true
    else
        echo "Failed to connect to remote PostgreSQL"
    fi
fi

# If no database is available, exit with error
if [ "$DB_CONNECTED" = false ]; then
    echo "ERROR: Could not connect to any PostgreSQL database (local or remote)"
    exit 1
fi

# Update database connection string
echo "Updating database connection string..."
export DATABASE_URL="postgresql://${ACTIVE_POSTGRES_USER}:${ACTIVE_POSTGRES_PASSWORD}@${ACTIVE_POSTGRES_HOST}:${ACTIVE_POSTGRES_PORT}/${ACTIVE_POSTGRES_DB}"
echo "Using database: ${ACTIVE_POSTGRES_HOST}:${ACTIVE_POSTGRES_PORT}/${ACTIVE_POSTGRES_DB}"

# Run database migrations
echo "Running database migrations with ${ACTIVE_POSTGRES_HOST} PostgreSQL..."
python -c "
import os
from sqlalchemy import create_engine
from src.models_db import Base

# Get the active database URL
db_url = os.environ.get('DATABASE_URL')
print('Connecting to database: ' + db_url.replace(db_url.split(':')[2].split('@')[0], '****'))

# Create engine with the active database
engine = create_engine(db_url)

print('Creating database tables if they do not exist...')
Base.metadata.create_all(bind=engine)
print('Database setup completed!')
"

# Check for Ollama service
echo "Checking if Ollama service is available..."
if curl -s --connect-timeout 5 http://ollama:11434/ > /dev/null 2>&1; then
    echo "Ollama is running"
    
    # If OLLAMA_MODEL is defined, check if it's available
    if [ -n "$OLLAMA_MODEL" ]; then
        echo "Checking if model $OLLAMA_MODEL is available..."
        if curl -s http://ollama:11434/api/tags 2>/dev/null | grep -q "$OLLAMA_MODEL"; then
            echo "Model $OLLAMA_MODEL is already available"
        else
            echo "Pulling model $OLLAMA_MODEL..."
            curl -X POST http://ollama:11434/api/pull -d "{\"name\":\"$OLLAMA_MODEL\"}" 2>/dev/null
            echo "Model $OLLAMA_MODEL pull initiated"
        fi
    fi
else
    echo "Ollama service is not available. The API will continue but LLM features may not work."
fi

# Run the API server
echo "Starting API server..."
exec uvicorn src.main:app --host 0.0.0.0 --port ${API_PORT:-8000}