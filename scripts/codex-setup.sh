#!/bin/bash

# Codex Setup Script
# This script installs Docker on Ubuntu systems
# Based on official Docker installation instructions

set -e  # Exit on any error

echo "🚀 Starting Codex Setup..."
echo "📦 Installing Docker on Ubuntu..."

# Check if running on Ubuntu
if ! grep -q "Ubuntu" /etc/os-release; then
    echo "❌ Error: This script is designed for Ubuntu systems only."
    exit 1
fi

# Update package index
echo "📋 Updating package index..."
sudo apt-get update

# Install prerequisite packages
echo "🔧 Installing prerequisite packages..."
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Create directory for Docker's GPG key
echo "🔑 Setting up Docker's GPG key..."
sudo install -m 0755 -d /etc/apt/keyrings

# Add Docker's official GPG key
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add Docker repository to Apt sources
echo "📦 Adding Docker repository..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index again
echo "🔄 Updating package index with Docker repository..."
sudo apt-get update

# Install Docker Engine
echo "🐳 Installing Docker Engine..."
sudo apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

# Start and enable Docker service
echo "🔄 Starting Docker service..."
if command -v systemctl >/dev/null 2>&1 && systemctl is-system-running >/dev/null 2>&1; then
    # System uses systemd
    sudo systemctl start docker
    sudo systemctl enable docker
    echo "✅ Docker service started and enabled via systemd"
elif command -v service >/dev/null 2>&1; then
    # Fallback to service command
    sudo service docker start
    echo "✅ Docker service started via service command"
else
    # Manual start for environments without init system
    echo "⚠️  No init system detected. Starting Docker daemon manually..."
    if ! pgrep dockerd >/dev/null; then
        sudo dockerd --host=unix:///var/run/docker.sock --host=tcp://0.0.0.0:2376 >/dev/null 2>&1 &
        sleep 3
        echo "✅ Docker daemon started manually"
    else
        echo "✅ Docker daemon is already running"
    fi
fi

# Add current user to docker group (if not root)
if [ "$EUID" -ne 0 ]; then
    echo "👤 Adding current user to docker group..."
    sudo usermod -aG docker $USER
    echo "⚠️  Note: You'll need to log out and back in for group changes to take effect."
fi

# Verify Docker installation
echo "✅ Verifying Docker installation..."
# Wait a moment for Docker daemon to be ready
sleep 2

# Check if Docker daemon is accessible
if docker info >/dev/null 2>&1; then
    echo "🐳 Docker daemon is running, testing with hello-world..."
    docker run hello-world
elif sudo docker info >/dev/null 2>&1; then
    echo "🐳 Docker daemon is running (requires sudo), testing with hello-world..."
    sudo docker run hello-world
else
    echo "⚠️  Docker daemon might not be fully ready yet."
    echo "   Try running 'docker run hello-world' manually in a few moments."
fi

echo ""
echo "🎉 Docker installation completed successfully!"
echo ""
echo "📝 Next steps:"
if command -v systemctl >/dev/null 2>&1 && systemctl is-system-running >/dev/null 2>&1; then
    echo "   1. Log out and log back in to use Docker without sudo"
    echo "   2. Or run 'newgrp docker' to apply group changes in current session"
    echo "   3. Test with: docker run hello-world"
else
    echo "   1. In non-systemd environments, you may need to start Docker manually:"
    echo "      sudo dockerd --host=unix:///var/run/docker.sock &"
    echo "   2. Log out and log back in to use Docker without sudo"
    echo "   3. Or run 'newgrp docker' to apply group changes in current session"
    echo "   4. Test with: docker run hello-world"
fi
echo ""
echo "🔗 Useful commands:"
echo "   - Check Docker version: docker --version"
echo "   - View running containers: docker ps"
echo "   - View all containers: docker ps -a"
echo "   - View images: docker images"
echo ""
echo "✨ Codex setup complete!" 