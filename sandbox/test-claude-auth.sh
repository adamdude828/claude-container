#!/bin/bash

# Test Claude authentication in a Docker container
# This script creates a minimal container that mounts .claude directory
# and tests if claude CLI is authenticated

set -e

echo "Testing Claude authentication in Docker container..."

# Check if .claude directory exists in home
if [ ! -d "$HOME/.claude" ]; then
    echo "Error: $HOME/.claude directory not found"
    echo "Please ensure Claude is installed and authenticated on the host first"
    exit 1
fi

# Check if authentication file exists
if [ ! -f "$HOME/.claude/config.json" ]; then
    echo "Error: $HOME/.claude/config.json not found"
    echo "Please ensure Claude is authenticated on the host first"
    exit 1
fi

# Build and run container with mounted .claude and .claude.settings directories
docker run --rm \
    -v "$HOME/.claude:/root/.claude" \
    -v "$HOME/.claude.settings:/root/.claude.settings" \
    -e CLAUDE_CONFIG_DIR=/root/.claude \
    node:20-slim \
    bash -c '
        # Install Claude in container
        echo "Installing Claude CLI..."
        npm install -g @anthropic-ai/claude-code >/dev/null 2>&1
        
        # Test Claude authentication
        echo "Testing Claude authentication..."
        claude -p "hello" --model=opus
        
        if [ $? -eq 0 ]; then
            echo "✅ SUCCESS: Claude is authenticated and working!"
            exit 0
        else
            echo "❌ FAILED: Claude authentication test failed"
            exit 1
        fi
    '

# Check exit status
if [ $? -eq 0 ]; then
    echo "Authentication test completed successfully!"
else
    echo "Authentication test failed!"
    exit 1
fi