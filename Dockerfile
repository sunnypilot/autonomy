FROM python:3.12-slim

# Install system dependencies
RUN apt update && apt install -y \
    git \
    git-lfs \
    zlib1g-dev \
    libeigen3-dev \
    ffmpeg \
    libglfw3-dev \
    llvm \
    libssl-dev \
    libzmq3-dev \
    gcc-arm-none-eabi \
    portaudio19-dev \
    gcc-13 \
    g++ \
    clang \
    libssl-dev \
    curl \
    libgdal-dev \
    jq \
    gh \
    && rm -rf /var/lib/apt/lists/*

# Install uv and create virtual environment
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:/root/.local/bin:$PATH"

# Set working directory
WORKDIR /__w/autonomy/autonomy

# Copy dependencies
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN bash -c ". /opt/venv/bin/activate && uv sync --extra testing"
