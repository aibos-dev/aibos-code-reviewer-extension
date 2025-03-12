FROM python:3.10

# Set the working directory
WORKDIR /app

# Install dependencies including `curl` and network tools
RUN apt-get update && apt-get install -y \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml requirements.txt ./

# Copy source code
COPY src/ src/
COPY sh/ sh/

# Make the scripts executable
RUN chmod +x sh/startup.sh

# Install dependencies with standard pip (more reliable)
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir python-dotenv  # Explicitly install the missing package

# Default command - will be overridden by docker-compose
CMD ["/app/sh/startup.sh"]