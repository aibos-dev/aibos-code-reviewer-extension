# Use Python 3.10 as the base image (changed from 3.12 to match what's being built)
FROM python:3.10

# Set the working directory
WORKDIR /app

# Install dependencies including `curl` for installing `uv`
RUN apt-get update && apt-get install -y \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install `uv`
RUN curl -fsSL https://astral.sh/uv/install.sh | sh

# Ensure `uv` is available in the PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml requirements.txt uv.lock ./

# Copy source code
COPY src/ src/
COPY sh/ sh/

# Make the scripts executable
RUN chmod +x sh/setup.sh sh/startup.sh

# Create virtual environment and install dependencies using `uv`
RUN uv venv && uv pip install --no-cache-dir -r requirements.txt

# Default command - will be overridden by docker-compose
CMD ["/app/sh/startup.sh"]