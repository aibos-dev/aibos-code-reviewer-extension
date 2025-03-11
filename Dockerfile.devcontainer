# Use the NVIDIA CUDA base image
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

ARG PYTHON_VERSION=3.12.4
ARG PYTHON_MAJOR=3.12
ARG NODE_VERSION=20  # or your choice

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
    OLLAMA_MODEL="deepseek-r1:70b"

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
       pciutils \
       lshw \
    #
    # Install Python from source
    && cd /usr/local/ \
    && wget https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tar.xz \
    && tar xvf Python-$PYTHON_VERSION.tar.xz \
    && cd /usr/local/Python-$PYTHON_VERSION \
    && ./configure --enable-optimizations \
    && make install \
    && rm -rf /usr/local/Python-$PYTHON_VERSION.tar.xz \
    && ln -fs /usr/local/Python-$PYTHON_VERSION/python /usr/bin/python \
    #
    # Install Node.js
    && curl -fsSL https://deb.nodesource.com/setup_$NODE_VERSION.x | bash - \
    && apt-get install -y nodejs \
    #
    # Verify Node
    && node -v && npm -v \
    #
    # Install Ollama script
    && cd /root \
    && curl -fsSL https://ollama.com/install.sh | sh \
    # Check if Ollama is installed
    && OLLAMA_BIN="$(which ollama)" \
    && if [ -z "$OLLAMA_BIN" ]; then \
         echo "ERROR: Ollama not found!"; \
         exit 1; \
       fi; \
    # Only copy if not already at /usr/local/bin/ollama
    if [ "$OLLAMA_BIN" != "/usr/local/bin/ollama" ]; then \
         cp "$OLLAMA_BIN" /usr/local/bin/ollama \
         && chmod 755 /usr/local/bin/ollama; \
       else \
         echo "Ollama already in /usr/local/bin, skipping copy!"; \
       fi \
    #
    # Cleanup
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/* /tmp/*

# Copy uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /workspace

COPY ./pyproject.toml ./uv.lock* /workspace/
RUN uv sync --frozen --no-install-project

ARG UID
ARG GID
ARG USERNAME
ARG GROUPNAME

RUN groupadd -g ${GID} ${GROUPNAME} -f && \
    useradd -m -s /bin/bash -u ${UID} -g ${GID} -c "Docker image user" ${USERNAME} && \
    chown -R ${USERNAME}:${GROUPNAME} /opt && \
    chown -R ${USERNAME}:${GROUPNAME} /usr/local

# For Node.js
RUN echo "export PATH=/usr/local/nvm/versions/node/v$NODE_VERSION/bin:\$PATH" >> ~/.bashrc

COPY sh/download_models.sh /usr/local/bin/download_models.sh
RUN chmod 755 /usr/local/bin/download_models.sh

USER ${USERNAME}:${GROUPNAME}

CMD ["sh", "-c", "ollama serve & sleep 5 && /usr/local/bin/download_models.sh && tail -f /dev/null"]
