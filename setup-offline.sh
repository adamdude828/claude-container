#!/bin/bash
# Setup script for Claude Container offline development
# Compatible with Ubuntu/Debian and macOS

set -e

echo "=== Claude Container Offline Setup ==="
echo

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    DISTRO=$(lsb_release -si 2>/dev/null || echo "unknown")
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
fi
echo "Detected OS: $OS"

# Check if Python 3.10+ is installed
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    if [[ "$OS" == "linux" ]]; then
        echo "Install with: sudo apt update && sudo apt install python3 python3-pip python3-venv"
    fi
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.10"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "Error: Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)"
    if [[ "$OS" == "linux" ]]; then
        echo "On Ubuntu 20.04 or newer, install with:"
        echo "sudo apt update && sudo apt install python3.10 python3.10-venv python3.10-dev"
    fi
    exit 1
fi
echo "✓ Python $PYTHON_VERSION found"

# Check for pip
if ! python3 -m pip --version &> /dev/null; then
    echo "Error: pip is not installed"
    if [[ "$OS" == "linux" ]]; then
        echo "Install with: sudo apt install python3-pip"
    fi
    exit 1
fi

# Check if Poetry is installed
echo "Checking Poetry installation..."
if ! command -v poetry &> /dev/null; then
    echo "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
    
    # Add to shell profile
    if [[ "$OS" == "linux" ]]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        echo "Added Poetry to ~/.bashrc - run 'source ~/.bashrc' or restart terminal"
    fi
fi
echo "✓ Poetry is installed"

# Install project dependencies
echo "Installing project dependencies..."
poetry install
echo "✓ Dependencies installed"

# Download wheel files for offline use
echo "Downloading dependency wheels for offline use..."
mkdir -p offline-wheels

# Export dependencies using pip freeze from poetry environment
poetry run pip freeze > requirements.txt
poetry run pip download -r requirements.txt -d offline-wheels/
rm requirements.txt
echo "✓ Dependency wheels downloaded to offline-wheels/"

# Create offline install script
cat > install-offline.sh << 'EOF'
#!/bin/bash
# Install Claude Container from offline wheels

set -e

echo "Installing Claude Container from offline wheels..."

# Install Poetry if not available
if ! command -v poetry &> /dev/null; then
    echo "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# Create requirements file from poetry.lock
poetry lock --no-update
poetry run pip freeze > requirements.txt

# Install dependencies from wheels
pip install --no-index --find-links offline-wheels/ -r requirements.txt
rm requirements.txt

# Install the project in development mode
poetry install --no-deps

echo "✓ Claude Container installed successfully"
echo "Run 'poetry shell' to activate the environment"
EOF

chmod +x install-offline.sh

echo
echo "=== Setup Complete ==="
echo "For offline installation on another machine:"
echo "1. Copy this entire directory including offline-wheels/"
echo "2. Run ./install-offline.sh"
echo
echo "To start development now:"
echo "1. Run: poetry shell"
echo "2. Test: claude-container --help"