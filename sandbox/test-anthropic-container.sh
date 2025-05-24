#!/bin/bash
# Test Anthropic's dev container setup

echo "Building Anthropic's Claude Code dev container..."

# Build the container
docker build -t claude-devcontainer \
  --build-arg TZ="America/Los_Angeles" \
  -f .devcontainer/Dockerfile \
  .devcontainer/

echo ""
echo "Creating volumes if they don't exist..."
docker volume create claude-code-bashhistory
docker volume create claude-code-config

echo ""
echo "Testing Claude Code installation in container..."


chmod +x test-in-container.sh

# Run the container with similar setup to devcontainer.json
docker run --rm \
  --cap-add=NET_ADMIN \
  --cap-add=NET_RAW \
  -v "$(pwd)":/workspace \
  -v claude-code-bashhistory:/commandhistory \
  -v claude-code-config:/home/node/.claude \
  -v "$HOME/.claude.json":/home/node/.claude.json:rw \
  -e NODE_OPTIONS="--max-old-space-size=4096" \
  -e CLAUDE_CONFIG_DIR="/home/node/.claude" \
  -e POWERLEVEL9K_DISABLE_GITSTATUS="true" \
  -u node \
  claude-devcontainer \
  /workspace/test-in-container.sh
