FROM ubuntu:24.04

# Install system dependencies
RUN apt update && apt install -y \
    python3.12 \
    python3.12-venv \
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
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="$PATH:/root/.local/bin"

# Create virtual environment
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /workspace

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv pip install -e .[testing,dev]

# Default command
CMD ["bash"]
