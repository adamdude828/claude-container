#!/bin/bash

# Test Claude authentication using API key approach
# This tests if Claude supports ANTHROPIC_API_KEY environment variable

set -e

echo "=== Claude API Key Authentication Test ==="
echo

# Check if ANTHROPIC_API_KEY is set on host
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "✓ Found ANTHROPIC_API_KEY in environment"
else
    echo "⚠️  No ANTHROPIC_API_KEY found in environment"
    echo "You may need to export ANTHROPIC_API_KEY=your-key-here"
fi

# Test 1: Mount .claude directory only
echo
echo "Test 1: Mounting .claude directory..."
docker run --rm \
    -v "$HOME/.claude:/root/.claude:rw" \
    -e CLAUDE_CONFIG_DIR=/root/.claude \
    node:20-slim \
    bash -c '
        npm install -g @anthropic-ai/claude-code >/dev/null 2>&1
        claude -p "hello" --model=opus 2>&1 || echo "Failed without API key"
    '

# Test 2: Pass API key if available
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo
    echo "Test 2: With ANTHROPIC_API_KEY..."
    docker run --rm \
        -v "$HOME/.claude:/root/.claude:rw" \
        -e CLAUDE_CONFIG_DIR=/root/.claude \
        -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
        node:20-slim \
        bash -c '
            npm install -g @anthropic-ai/claude-code >/dev/null 2>&1
            claude -p "hello" --model=opus 2>&1
        '
fi

# Test 3: Check what authentication methods Claude supports
echo
echo "Test 3: Checking Claude help for auth options..."
docker run --rm \
    node:20-slim \
    bash -c '
        npm install -g @anthropic-ai/claude-code >/dev/null 2>&1
        echo "=== Claude Help Output ==="
        claude --help 2>&1 | grep -A5 -B5 -i "auth\|api\|key\|login" || true
        echo
        echo "=== Environment variables Claude might use ==="
        claude --help 2>&1 | grep -i "env" || true
    '

echo
echo "Tests complete!"
echo
echo "Note: Claude uses OAuth authentication that stores tokens in system-specific"
echo "locations. For containerized environments, you may need to:"
echo "1. Use ANTHROPIC_API_KEY environment variable (if supported)"
echo "2. Complete OAuth flow inside the container"
echo "3. Use a different authentication method designed for CI/CD"