#!/bin/bash
# Test mounting npm global directory from host

echo "Finding npm global directory on host..."
NPM_GLOBAL=$(npm config get prefix)
echo "NPM global directory: $NPM_GLOBAL"

# Create test script
cat > test-npm-mount.sh << 'EOF'
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
EOF

chmod +x test-npm-mount.sh

# Try different approaches based on the npm global location
if [[ "$NPM_GLOBAL" == *"Application Support"* ]]; then
    echo "Detected path with spaces. Trying alternative mount approach..."
    
    # Create a symlink without spaces
    TEMP_LINK="/tmp/npm-global-link"
    rm -f "$TEMP_LINK"
    ln -s "$NPM_GLOBAL" "$TEMP_LINK"
    
    echo "Created temporary symlink: $TEMP_LINK -> $NPM_GLOBAL"
    
    docker run --rm \
      -v "$TEMP_LINK":/host-npm-global:ro \
      -v "${HOME}/.claude.json":/home/node/.claude.json:rw \
      -v "${HOME}/.claude":/home/node/.claude:rw \
      -v "$(pwd)":/workspace \
      -e CLAUDE_CONFIG_DIR="/home/node/.claude" \
      -u node \
      -w /workspace \
      claude-devcontainer \
      /workspace/test-npm-mount.sh
    
    rm -f "$TEMP_LINK"
else
    # Direct mount for paths without spaces
    docker run --rm \
      -v "$NPM_GLOBAL":/host-npm-global:ro \
      -v "${HOME}/.claude.json":/home/node/.claude.json:rw \
      -v "${HOME}/.claude":/home/node/.claude:rw \
      -v "$(pwd)":/workspace \
      -e CLAUDE_CONFIG_DIR="/home/node/.claude" \
      -u node \
      -w /workspace \
      claude-devcontainer \
      /workspace/test-npm-mount.sh
fi