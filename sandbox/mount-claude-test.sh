#!/bin/bash
# Test mounting Claude Code installation from host

# Claude Code installation path
CLAUDE_CODE_DIR="/Users/adamholsinger/Library/Application Support/Herd/config/nvm/versions/node/v18.20.4/lib/node_modules/@anthropic-ai/claude-code"

echo "Claude Code directory: $CLAUDE_CODE_DIR"

# Create a minimal Dockerfile without Claude Code
cat > Dockerfile.mount-test << 'EOF'
FROM node:20

# Install Python for any scripts that might need it
RUN apt-get update && apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p /root/.claude
RUN mkdir -p /usr/local/lib/node_modules/@anthropic-ai/claude-code

WORKDIR /workspace

CMD ["/bin/bash"]
EOF

# Build test image
echo "Building test image..."
docker build -f Dockerfile.mount-test -t claude-mount-test .

# Create a test script to run in container
cat > test-claude.sh << 'EOF'
#!/bin/bash
echo "Testing Claude Code mount..."
echo "Node version: $(node --version)"
echo "Current directory: $(pwd)"
echo ""

# Check if claude cli.js exists
if [ -f /usr/local/lib/node_modules/@anthropic-ai/claude-code/cli.js ]; then
    echo "✓ Claude Code cli.js found"
    
    # Try to run it
    echo ""
    echo "Testing claude --version:"
    node /usr/local/lib/node_modules/@anthropic-ai/claude-code/cli.js --version
    
    echo ""
    echo "Testing claude --help:"
    node /usr/local/lib/node_modules/@anthropic-ai/claude-code/cli.js --help | head -10
else
    echo "✗ Claude Code cli.js not found"
fi

echo ""
echo "Directory contents:"
ls -la /usr/local/lib/node_modules/@anthropic-ai/claude-code/ | head -10
EOF

chmod +x test-claude.sh

# Run container with Claude Code mounted
echo ""
echo "Running container with mounted Claude Code..."
docker run --rm \
  -v "$(pwd)":/workspace \
  -v "$HOME/.claude.json":/root/.claude.json:rw \
  -v "$HOME/.claude":/root/.claude:rw \
  -v "$CLAUDE_CODE_DIR":/usr/local/lib/node_modules/@anthropic-ai/claude-code:ro \
  claude-mount-test \
  /workspace/test-claude.sh