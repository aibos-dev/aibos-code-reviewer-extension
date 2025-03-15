#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "Setting up project environment..."

echo "Starting the application..."

# Try to connect to local PostgreSQL first
echo "Trying to connect to local PostgreSQL..."
MAX_DB_RETRIES=10
DB_RETRY_COUNT=0
LOCAL_DB_AVAILABLE=false

# Check if POSTGRES_HOST is defined
if [ -z "$POSTGRES_HOST" ]; then
    echo "POSTGRES_HOST is not defined. Setting default to postgres"
    export POSTGRES_HOST="postgres"
fi

while [ $DB_RETRY_COUNT -lt $MAX_DB_RETRIES ]; do
    if nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}" 2>/dev/null; then
        echo "Local PostgreSQL is available"
        LOCAL_DB_AVAILABLE=true
        
        # Set environment variables for local DB
        export ACTIVE_POSTGRES_HOST="${POSTGRES_HOST}"
        export ACTIVE_POSTGRES_PORT="${POSTGRES_PORT:-5432}"
        export ACTIVE_POSTGRES_USER="${POSTGRES_USER}"
        export ACTIVE_POSTGRES_PASSWORD="${POSTGRES_PASSWORD}"
        export ACTIVE_POSTGRES_DB="${POSTGRES_DB}"
        
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
    export ACTIVE_POSTGRES_HOST="${REMOTE_POSTGRES_HOST}"
    export ACTIVE_POSTGRES_PORT="${REMOTE_POSTGRES_PORT:-5432}"
    export ACTIVE_POSTGRES_USER="${REMOTE_POSTGRES_USER}"
    export ACTIVE_POSTGRES_PASSWORD="${REMOTE_POSTGRES_PASSWORD}"
    export ACTIVE_POSTGRES_DB="${REMOTE_POSTGRES_DB}"
    
    # Test connection to remote PostgreSQL
    if nc -z "${REMOTE_POSTGRES_HOST}" "${REMOTE_POSTGRES_PORT:-5432}" 2>/dev/null; then
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
        print('Connecting to database host: {}'.format(host_part))
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

# Wait for Ollama to be ready with increased timeout
echo "Checking if Ollama service is available..."
OLLAMA_RETRIES=30
OLLAMA_RETRY_COUNT=0
OLLAMA_AVAILABLE=false

while [ $OLLAMA_RETRY_COUNT -lt $OLLAMA_RETRIES ]; do
    if curl -s --connect-timeout 5 http://ollama:11434/ > /dev/null 2>&1; then
        echo "Ollama is running"
        OLLAMA_AVAILABLE=true
        break
    fi
    OLLAMA_RETRY_COUNT=$((OLLAMA_RETRY_COUNT+1))
    echo "Waiting for Ollama service... attempt $OLLAMA_RETRY_COUNT/$OLLAMA_RETRIES"
    sleep 5  # Increased sleep time
done

# If Ollama is available and OLLAMA_MODEL is defined, check/pull the model
if [ "$OLLAMA_AVAILABLE" = true ] && [ -n "$OLLAMA_MODEL" ]; then
    # Set OLLAMA_HOST environment variable to point to the Ollama container
    export OLLAMA_HOST=http://ollama:11434
    
    echo "Checking if model $OLLAMA_MODEL is available..."
    if curl -s http://ollama:11434/api/tags 2>/dev/null | grep -q "\"name\":\"$OLLAMA_MODEL\""; then
        echo "Model $OLLAMA_MODEL is already available"
    else
        echo "Pulling model $OLLAMA_MODEL. This may take several minutes..."
        # Show progress during model download
        curl -X POST http://ollama:11434/api/pull -d "{\"name\":\"$OLLAMA_MODEL\"}" | while read -r line; do
            echo "$line"
        done
        
        # Verify the model was successfully pulled
        if curl -s http://ollama:11434/api/tags 2>/dev/null | grep -q "\"name\":\"$OLLAMA_MODEL\""; then
            echo "Model $OLLAMA_MODEL successfully pulled and ready to use"
        else
            echo "WARNING: Failed to pull model $OLLAMA_MODEL. The API will continue, but LLM features may not work."
        fi
    fi
    
    # Check for GPU availability in Ollama
    GPU_INFO=$(curl -s http://ollama:11434/api/info 2>/dev/null)
    if echo "$GPU_INFO" | grep -q "\"cuda\""; then
        echo "GPU acceleration is available for Ollama"
        echo "$GPU_INFO" | grep -E "\"cuda\"|\"gpu\"" | sed 's/,$//'
    else
        echo "WARNING: No GPU acceleration detected for Ollama. Performance may be slower."
    fi
    
elif [ "$OLLAMA_AVAILABLE" = false ]; then
    echo "Ollama service is not available. The API will continue but LLM features may not work."
fi

# Run the API server
echo "Starting API server..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000