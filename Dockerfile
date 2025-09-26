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
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv and create virtual environment
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:/root/.local/bin:$PATH"

# Set working directory
WORKDIR /__w/autonomy/autonomy

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN bash -c ". /opt/venv/bin/activate && uv pip install -e .[testing]"

# Default command
CMD ["bash"]
