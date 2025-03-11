#!/bin/bash
set -e

echo "Starting entrypoint script..."

# Run setup
/app/sh/setup.sh

# Run startup
exec /app/sh/startup.sh