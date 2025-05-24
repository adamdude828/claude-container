#!/bin/bash
echo "=== Testing NPM Global Mount ==="
echo ""
echo "User: $(whoami)"
echo "Home: $HOME"
echo ""

echo "Checking mounted npm global:"
ls -la /host-npm-global/
echo ""

echo "Looking for Claude Code:"
find /host-npm-global -name "claude" -type f 2>/dev/null | head -5
echo ""

# Find the claude binary
CLAUDE_BIN=$(find /host-npm-global -name "claude" -type f -path "*/bin/*" 2>/dev/null | head -1)
if [ -n "$CLAUDE_BIN" ]; then
    echo "Found claude at: $CLAUDE_BIN"
    echo "Setting up symlink..."
    ln -sf "$CLAUDE_BIN" /usr/local/bin/claude
    
    echo ""
    echo "Testing claude --version:"
    claude --version 2>&1 || echo "Failed to run claude"
else
    echo "Claude binary not found in mounted npm global"
fi
