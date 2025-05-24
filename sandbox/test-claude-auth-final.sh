#!/bin/bash

# Test Claude authentication in a Docker container
# Mounts both .claude and .claude.settings directories as specified

set -e

echo "=== Claude Container Authentication Test ==="
echo

# Check prerequisites
echo "Checking host system..."
if [ ! -d "$HOME/.claude" ]; then
    echo "❌ Error: $HOME/.claude directory not found"
    exit 1
fi
echo "✓ Found .claude directory"

if [ ! -d "$HOME/.claude.settings" ]; then
    echo "⚠️  Warning: $HOME/.claude.settings directory not found"
    echo "  Creating empty directory..."
    mkdir -p "$HOME/.claude.settings"
fi
echo "✓ Found/created .claude.settings directory"

# Run the test
echo
echo "Running Claude authentication test in container..."
echo "Mounting:"
echo "  - $HOME/.claude -> /root/.claude"
echo "  - $HOME/.claude.settings -> /root/.claude.settings"
echo

docker run --rm \
    -v "$HOME/.claude:/root/.claude" \
    -v "$HOME/.claude.settings:/root/.claude.settings" \
    -e CLAUDE_CONFIG_DIR=/root/.claude \
    node:20-slim \
    bash -c '
        echo "Installing Claude CLI..."
        npm install -g @anthropic-ai/claude-code >/dev/null 2>&1
        
        echo "Claude version: $(claude --version 2>&1 || echo "unknown")"
        echo
        
        echo "Testing: claude -p \"hello\" --model=opus"
        claude -p "hello" --model=opus
    '

EXIT_CODE=$?

echo
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ SUCCESS: Claude is authenticated and working in the container!"
else
    echo "❌ FAILED: Claude authentication test failed (exit code: $EXIT_CODE)"
    echo
    echo "This might be because:"
    echo "1. Claude uses OAuth tokens stored outside these directories"
    echo "2. Additional authentication setup is needed in the container"
    echo "3. The host Claude session needs to be refreshed"
fi

exit $EXIT_CODE