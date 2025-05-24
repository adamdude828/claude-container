#!/bin/bash
# Test with host Claude config mounted

echo "Testing with host Claude configuration..."

# Run interactively to see what happens
docker run -it --rm \
  --cap-add=NET_ADMIN \
  --cap-add=NET_RAW \
  -v "$(pwd)":/workspace \
  -v claude-code-bashhistory:/commandhistory \
  -v "$HOME/.claude":/home/node/.claude:rw \
  -v "$HOME/.claude.json":/home/node/.claude.json:rw \
  -e NODE_OPTIONS="--max-old-space-size=4096" \
  -e CLAUDE_CONFIG_DIR="/home/node/.claude" \
  -e POWERLEVEL9K_DISABLE_GITSTATUS="true" \
  -u node \
  claude-devcontainer \
  /bin/bash