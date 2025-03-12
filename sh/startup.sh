#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

echo "Starting the application..."

# Try to connect to local PostgreSQL first
echo "Trying to connect to local PostgreSQL..."
MAX_DB_RETRIES=10
DB_RETRY_COUNT=0
LOCAL_DB_AVAILABLE=false

while [ $DB_RETRY_COUNT -lt $MAX_DB_RETRIES ]; do
    if nc -z ${POSTGRES_HOST} 5432; then
        echo "Local PostgreSQL is available"
        LOCAL_DB_AVAILABLE=true
        
        # Set environment variables for local DB
        export ACTIVE_POSTGRES_HOST=${POSTGRES_HOST}
        export ACTIVE_POSTGRES_PORT=${POSTGRES_PORT}
        export ACTIVE_POSTGRES_USER=${POSTGRES_USER}
        export ACTIVE_POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
        export ACTIVE_POSTGRES_DB=${POSTGRES_DB}
        
        break
    fi
    DB_RETRY_COUNT=$((DB_RETRY_COUNT+1))
    echo "Waiting for local PostgreSQL... attempt $DB_RETRY_COUNT/$MAX_DB_RETRIES"
    sleep 2
done

# If local PostgreSQL is not available and remote credentials are provided, try remote
if [ "$LOCAL_DB_AVAILABLE" = false ] && [ -n "$REMOTE_POSTGRES_HOST" ]; then
    echo "Local PostgreSQL not available. Attempting to connect to remote PostgreSQL..."
    
    # Set environment variables for remote DB
    export ACTIVE_POSTGRES_HOST=${REMOTE_POSTGRES_HOST}
    export ACTIVE_POSTGRES_PORT=${REMOTE_POSTGRES_PORT}
    export ACTIVE_POSTGRES_USER=${REMOTE_POSTGRES_USER}
    export ACTIVE_POSTGRES_PASSWORD=${REMOTE_POSTGRES_PASSWORD}
    export ACTIVE_POSTGRES_DB=${REMOTE_POSTGRES_DB}
    
    # Test connection to remote PostgreSQL
    if nc -z ${REMOTE_POSTGRES_HOST} ${REMOTE_POSTGRES_PORT}; then
        echo "Remote PostgreSQL is available"
        LOCAL_DB_AVAILABLE=true  # Set to true as we found a working DB
    else
        echo "ERROR: Remote PostgreSQL not responding"
        LOCAL_DB_AVAILABLE=false
    fi
fi

# If no database is available, exit with error
if [ "$LOCAL_DB_AVAILABLE" = false ]; then
    echo "ERROR: No PostgreSQL database available (local or remote)"
    exit 1
fi

# Update database connection string
echo "Updating database connection string..."
export DATABASE_URL="postgresql://${ACTIVE_POSTGRES_USER}:${ACTIVE_POSTGRES_PASSWORD}@${ACTIVE_POSTGRES_HOST}:${ACTIVE_POSTGRES_PORT}/${ACTIVE_POSTGRES_DB}"

# Run database migrations
echo "Running database migrations with ${ACTIVE_POSTGRES_HOST} PostgreSQL..."
python -c "
import os
from sqlalchemy import create_engine
from src.models_db import Base

# Get the active database URL
db_url = os.environ.get('DATABASE_URL')
# Safely extract host from URL for logging
try:
    # Handle cases where @ might not be in the URL
    if '@' in db_url:
        host_part = db_url.split('@')[1].split(':')[0]
        print(f'Connecting to database host: {host_part}')
    else:
        print('Connecting to database (could not parse URL)')
except Exception as e:
    print('Connecting to database (could not parse URL)')

# Create engine with the active database
engine = create_engine(db_url)

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