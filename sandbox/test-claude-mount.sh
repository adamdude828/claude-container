#!/bin/bash
# Test mounting Claude Code from host

# Find where Claude Code is installed
CLAUDE_CODE_PATH=$(which claude)
if [ -z "$CLAUDE_CODE_PATH" ]; then
    echo "Claude Code not found in PATH"
    exit 1
fi

# Get the actual installation directory
CLAUDE_BIN_DIR=$(dirname "$CLAUDE_CODE_PATH")
echo "Claude binary at: $CLAUDE_BIN_DIR"

# Find the node_modules path (Claude Code is an npm package)
# It's usually in a node_modules/@anthropic-ai/claude-code directory
CLAUDE_NODE_MODULES=$(cd "$CLAUDE_BIN_DIR" && cd .. && pwd)
echo "Node modules at: $CLAUDE_NODE_MODULES"

# Let's also find where npm global packages are installed
NPM_GLOBAL=$(npm root -g)
echo "NPM global packages at: $NPM_GLOBAL"

# Create a test Dockerfile that doesn't install Claude Code
cat > Dockerfile.test << 'EOF'
FROM node:20

# Don't install Claude Code - we'll mount it from host
# Just create the directories we need
RUN mkdir -p /root/.claude

WORKDIR /workspace

# We'll mount the Claude Code binary and node_modules
CMD ["/bin/bash"]
EOF

# Build test image
echo "Building test image..."
docker build -f Dockerfile.test -t claude-mount-test .

# Run container with Claude Code mounted from host
echo "Running container with mounted Claude Code..."
docker run -it --rm \
  -v "$(pwd)":/workspace \
  -v ~/.claude.json:/root/.claude.json:rw \
  -v ~/.claude:/root/.claude:rw \
  -v "$NPM_GLOBAL/@anthropic-ai/claude-code":/usr/local/lib/node_modules/@anthropic-ai/claude-code:ro \
  -v "$CLAUDE_BIN_DIR/claude":/usr/local/bin/claude:ro \
  claude-mount-test \
  /bin/bash