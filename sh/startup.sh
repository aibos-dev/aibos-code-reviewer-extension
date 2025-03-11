#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

echo "Starting the application..."

# Wait for Ollama to be ready
echo "Waiting for Ollama service..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://ollama:11434/ > /dev/null; then
        echo "Ollama is running"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT+1))
    echo "Waiting for Ollama service... attempt $RETRY_COUNT/$MAX_RETRIES"
    sleep 5
done

# Check if Ollama is running
if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "WARNING: Ollama not responding after $MAX_RETRIES attempts, but continuing anyway"
fi

# If OLLAMA_MODEL is defined, try to pull it
if [ -n "$OLLAMA_MODEL" ]; then
    echo "Ensuring model $OLLAMA_MODEL is available..."
    # Try using the direct ollama command instead of API calls
    if curl -s http://ollama:11434/api/tags | grep -q "$OLLAMA_MODEL"; then
        echo "Model $OLLAMA_MODEL already exists"
    else
        echo "Pulling model $OLLAMA_MODEL..."
        # Set a timeout for the pull operation
        timeout 300 curl -X POST http://ollama:11434/api/pull -d "{\"name\":\"$OLLAMA_MODEL\"}"
        if [ $? -ne 0 ]; then
            echo "WARNING: Model pull timed out or failed, but continuing anyway"
        fi
    fi
fi

# Run the API server
echo "Starting API server..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000