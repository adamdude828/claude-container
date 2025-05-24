#!/bin/bash
# Approve dangerously-skip-permissions interactively

echo "This will run Claude interactively to approve --dangerously-skip-permissions"
echo "You'll need to confirm when prompted."
echo ""

# Run with the anthropic container setup
docker run -it --rm \
  --cap-add=NET_ADMIN \
  --cap-add=NET_RAW \
  -v "$(pwd)":/workspace \
  -v claude-code-bashhistory:/commandhistory \
  -v "$HOME/.claude":/home/node/.claude:rw \
  -v "$HOME/.claude.json":/home/node/.claude.json:rw \
  -e NODE_OPTIONS="--max-old-space-size=4096" \
  -e CLAUDE_CONFIG_DIR="/home/node/.claude" \
  -u node \
  claude-devcontainer \
  bash -c "claude --dangerously-skip-permissions -p 'say hello' --print"