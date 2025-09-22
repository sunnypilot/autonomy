#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
ROOT="$(cd $DIR/../ && pwd)"
ARCH=$(uname -m)

# homebrew update is slow
export HOMEBREW_NO_AUTO_UPDATE=1

if [[ $SHELL == "/bin/zsh" ]]; then
  RC_FILE="$HOME/.zshrc"
elif [[ $SHELL == "/bin/bash" ]]; then
  RC_FILE="$HOME/.bash_profile"
fi

# Install brew if required
if [[ $(command -v brew) == "" ]]; then
  echo "Installing Homebrew"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  echo "[ ] installed brew t=$SECONDS"

  # make brew available now
  if [[ $ARCH == "x86_64" ]]; then
    echo 'eval "$(/usr/local/bin/brew shellenv)"' >> $RC_FILE
    eval "$(/usr/local/bin/brew shellenv)"
  else
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> $RC_FILE
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi
else
    brew up
fi

brew install python@3.12. # install python if not already installed
python3.12 -m venv .venv
source .venv/bin/activate

brew bundle --file=- <<-EOS
brew "git-lfs"
brew "zlib"
brew "eigen"
brew "ffmpeg"
brew "glfw"
brew "llvm"
brew "openssl@3.0"
EOS

echo "[ ] finished brew install t=$SECONDS"

BREW_PREFIX=$(brew --prefix)

# archive backend tools for pip dependencies
export LDFLAGS="$LDFLAGS -L${BREW_PREFIX}/opt/zlib/lib"
export LDFLAGS="$LDFLAGS -L${BREW_PREFIX}/opt/bzip2/lib"
export CPPFLAGS="$CPPFLAGS -I${BREW_PREFIX}/opt/zlib/include"
export CPPFLAGS="$CPPFLAGS -I${BREW_PREFIX}/opt/bzip2/include"

# pycurl curl/openssl backend dependencies
export LDFLAGS="$LDFLAGS -L${BREW_PREFIX}/opt/openssl@3/lib"
export CPPFLAGS="$CPPFLAGS -I${BREW_PREFIX}/opt/openssl@3/include"
export PYCURL_CURL_CONFIG=/usr/bin/curl-config
export PYCURL_SSL_LIBRARY=openssl

# install python dependencies
pip install -e .
echo "[ ] installed python dependencies t=$SECONDS"

echo
echo "---   Mac setup complete  ---"
echo "Open a new shell or configure your active shell env by running:"
echo "source .venv/bin/activate"
