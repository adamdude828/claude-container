#!/bin/bash
echo "=== Testing Mounted Claude Code ==="
echo ""
echo "User: $(whoami)"
echo "Home: $HOME"
echo ""

echo "Checking mounted Claude Code:"
ls -la /host-claude-code/
echo ""

echo "Setting up symlink:"
ln -sf /host-claude-code/bin/claude /usr/local/bin/claude
echo ""

echo "Claude version:"
claude --version
echo ""

echo "Environment variables:"
env | grep -E "(CLAUDE|NODE_OPTIONS|NPM)" | sort
echo ""

echo "Checking .claude.json:"
if [ -f ~/.claude.json ]; then
    echo "✓ .claude.json exists"
    echo "File permissions: $(ls -la ~/.claude.json)"
else
    echo "✗ .claude.json not found"
fi
echo ""

echo "Testing API call:"
claude -p "say hello" --model=opus 2>&1 || true
