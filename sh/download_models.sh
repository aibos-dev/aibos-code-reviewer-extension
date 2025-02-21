#!/bin/bash

echo "Checking if DeepSeek R1 70B model is available..."
if ollama list | grep -q "deepseek-r1:70b"; then
    echo "DeepSeek R1 70B is already downloaded."
else
    echo "Downloading DeepSeek R1 70B model..."
    ollama pull deepseek-r1:70b
    echo "Download completed."
fi
