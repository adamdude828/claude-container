#!/bin/bash

# Simple test for Claude authentication in Docker
# This script assumes Claude uses OAuth tokens that may need additional setup

set -e

echo "=== Claude Container Authentication Test ==="
echo

# Check prerequisites
if [ ! -d "$HOME/.claude" ]; then
    echo "❌ Error: $HOME/.claude directory not found"
    echo "Please ensure Claude is installed and authenticated on the host first"
    exit 1
fi

echo "✓ Found .claude directory"

# Check if we can find any auth-related environment variables
echo
echo "Checking for Claude-related environment variables..."
env | grep -i claude || echo "No CLAUDE env vars found"

# Create a minimal Dockerfile for testing
cat > Dockerfile.claude-test << 'EOF'
FROM node:20-slim

# Create non-root user
RUN useradd -m -s /bin/bash claude

# Install Claude globally
RUN npm install -g @anthropic-ai/claude-code

# Switch to claude user
USER claude
WORKDIR /home/claude

# Set environment
ENV CLAUDE_CONFIG_DIR=/home/claude/.claude

CMD ["claude", "-p", "hello", "--model=opus"]
EOF

echo
echo "Building test container..."
docker build -t claude-auth-test -f Dockerfile.claude-test .

echo
echo "Running test with mounted .claude directory..."
docker run --rm \
    -v "$HOME/.claude:/home/claude/.claude:rw" \
    claude-auth-test

# Cleanup
rm -f Dockerfile.claude-test

echo
echo "Test complete!"