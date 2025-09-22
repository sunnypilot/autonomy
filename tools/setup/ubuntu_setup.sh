#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
ROOT="$(cd $DIR/../ && pwd)"


sudo apt update

# Install Python 3.12 if not already installed
sudo apt install -y python3.12 python3.12-venv
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
python3.12 -m venv .venv
source .venv/bin/activate

# Install packages
sudo apt install -y git-lfs zlib1g-dev libeigen3-dev ffmpeg libglfw3-dev llvm libssl-dev libzmq3-dev gcc-arm-none-eabi portaudio19-dev gcc-13
echo "[ ] finished apt install t=$SECONDS"


# install python dependencies
uv pip install -e .[testing, simulator]
echo "[ ] installed python dependencies t=$SECONDS"

echo
echo "---   Ubuntu setup complete  ---"
echo "Open a new shell or configure your active shell env by running:"
echo "source ~/.bashrc"
