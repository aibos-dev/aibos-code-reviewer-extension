# Use the NVIDIA CUDA base image
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

ARG PYTHON_VERSION=3.12.4
ARG PYTHON_MAJOR=3.12
ARG NODE_VERSION=20  # Change to the desired Node.js version

ENV TZ=Asia/Tokyo \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    PYTHONIOENCODING=utf-8 \
    DEBIAN_FRONTEND=noninteractive \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=python$PYTHON_MAJOR \
    UV_PROJECT_ENVIRONMENT="/usr/local/" \
    NVM_DIR="/usr/local/nvm" \
    NODE_VERSION=$NODE_VERSION \
    PATH="/usr/local/nvm/versions/node/v$NODE_VERSION/bin:$PATH" \
    OLLAMA_MODEL="deepseek-r1-70b"

# Install system dependencies, build Python from source, and install Node.js
WORKDIR /tmp/
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && apt-get update && apt-get install -y --no-install-recommends \
    git \
    zip \
    wget \
    curl \
    make \
    llvm \
    ffmpeg \
    tzdata \
    tk-dev \
    graphviz \
    xz-utils \
    zlib1g-dev \
    libssl-dev \
    libbz2-dev \
    libffi-dev \
    liblzma-dev \
    libsqlite3-dev \
    libgl1-mesa-dev \
    libreadline-dev \
    libncurses5-dev \
    libncursesw5-dev \
    build-essential \
    #
    # Install Python from source
    && cd /usr/local/ && wget https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tar.xz \
    && tar xvf Python-$PYTHON_VERSION.tar.xz \
    && cd /usr/local/Python-$PYTHON_VERSION \
    && ./configure --enable-optimizations \
    && make install \
    && rm -rf /usr/local/Python-$PYTHON_VERSION.tar.xz \
    && ln -fs /usr/local/Python-$PYTHON_VERSION/python /usr/bin/python \
    #
    # Install Node.js using NodeSource
    && curl -fsSL https://deb.nodesource.com/setup_$NODE_VERSION.x | bash - \
    && apt-get install -y nodejs \
    #
    # Verify installations
    && node -v && npm -v \
    #
    # Install Ollama properly
    && curl -fsSL https://ollama.com/install.sh | sh \
    && ln -s /root/.ollama/bin/ollama /usr/local/bin/ollama \
    #
    # Cleanup to reduce image size
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/* /tmp/*

# Copy uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set up the workspace
WORKDIR /workspace
COPY ./pyproject.toml ./uv.lock* /workspace/
RUN uv sync --frozen --no-install-project

# Set up user permissions
ARG UID
ARG GID
ARG USERNAME
ARG GROUPNAME
RUN groupadd -g ${GID} ${GROUPNAME} -f && \
    useradd -m -s /bin/bash -u ${UID} -g ${GID} -c "Docker image user" ${USERNAME} && \
    chown -R ${USERNAME}:${GROUPNAME} /opt && \
    chown -R ${USERNAME}:${GROUPNAME} /usr/local

USER ${USERNAME}:${GROUPNAME}

# Ensure Node.js and npm are accessible in every shell
RUN echo "export PATH=/usr/local/nvm/versions/node/v$NODE_VERSION/bin:\$PATH" >> ~/.bashrc

# Copy startup script for Ollama model download
COPY sh/download_models.sh /usr/local/bin/download_models.sh
RUN chmod +x /usr/local/bin/download_models.sh

# Start Ollama and ensure model download
CMD ["sh", "-c", "ollama serve & sleep 5 && /usr/local/bin/download_models.sh && tail -f /dev/null"]
