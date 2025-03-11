#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "Setting up project environment..."

# Wait for Ollama to be ready
echo "Waiting for Ollama service..."
for i in {1..30}; do
    if curl -s http://ollama:11434/ > /dev/null; then
        echo "Ollama is running"
        break
    fi
    echo "Waiting for Ollama service... attempt $i/30"
    sleep 2
done

# Check if Ollama is running
if ! curl -s http://ollama:11434/ > /dev/null; then
    echo "ERROR: Ollama failed to start after 30 attempts"
    exit 1
fi

# Pull Ollama model
if [ -n "$OLLAMA_MODEL" ]; then
    echo "Pulling Ollama model: $OLLAMA_MODEL"
    # Set OLLAMA_HOST environment variable to point to the Ollama container
    export OLLAMA_HOST=http://ollama:11434
    
    # Check if model exists
    if curl -s http://ollama:11434/api/tags | grep -q "$OLLAMA_MODEL"; then
        echo "Model $OLLAMA_MODEL already exists"
    else
        echo "Pulling model $OLLAMA_MODEL..."
        curl -X POST http://ollama:11434/api/pull -d "{\"name\":\"$OLLAMA_MODEL\"}"
    fi
fi

echo "Setup complete."