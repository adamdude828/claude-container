#!/bin/bash
# Test mounting Claude Code from host

echo "Testing Claude Code mounted from host..."

# Find Claude Code installation on host
CLAUDE_PATH=$(which claude)
if [ -z "$CLAUDE_PATH" ]; then
    echo "Error: Claude not found on host"
    exit 1
fi

# Get the actual installation directory
CLAUDE_REAL_PATH=$(readlink -f "$CLAUDE_PATH")
CLAUDE_BIN_DIR=$(dirname "$CLAUDE_REAL_PATH")
CLAUDE_INSTALL_DIR=$(dirname "$CLAUDE_BIN_DIR")
echo "Found Claude Code at: $CLAUDE_INSTALL_DIR"
echo "Claude binary: $CLAUDE_REAL_PATH"

# Create test script
cat > test-mounted-claude.sh << 'EOF'
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
EOF

chmod +x test-mounted-claude.sh

# Run container with Claude Code mounted from host
echo "Running container with mounted Claude Code..."
docker run --rm \
  -v "${CLAUDE_INSTALL_DIR}":/host-claude-code:ro \
  -v "${HOME}/.claude.json":/home/node/.claude.json:rw \
  -v "${HOME}/.claude":/home/node/.claude:rw \
  -v "$(pwd)":/workspace \
  -e CLAUDE_CONFIG_DIR="/home/node/.claude" \
  -e NODE_OPTIONS="--max-old-space-size=4096" \
  -u node \
  -w /workspace \
  claude-devcontainer \
  /workspace/test-mounted-claude.sh