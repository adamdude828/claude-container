#!/bin/bash
# Test Claude Code with mounted binary and auth

CLAUDE_CODE_DIR="/Users/adamholsinger/Library/Application Support/Herd/config/nvm/versions/node/v18.20.4/lib/node_modules/@anthropic-ai/claude-code"

# Create a simple hello world script for Claude to write
cat > test-task.sh << 'EOF'
#!/bin/bash
echo "Testing Claude Code authentication..."
echo ""
echo "Running: node /usr/local/lib/node_modules/@anthropic-ai/claude-code/cli.js -p 'say hello' --print"
node /usr/local/lib/node_modules/@anthropic-ai/claude-code/cli.js -p "say hello" --print

echo ""
echo "Exit code: $?"
EOF

chmod +x test-task.sh

# Run the test
docker run --rm \
  -v "$(pwd)":/workspace \
  -v "$HOME/.claude.json":/root/.claude.json:rw \
  -v "$HOME/.claude":/root/.claude:rw \
  -v "$CLAUDE_CODE_DIR":/usr/local/lib/node_modules/@anthropic-ai/claude-code:ro \
  claude-mount-test \
  /workspace/test-task.sh