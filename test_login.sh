#!/bin/bash
# Test script to check claude login in container

cd /Users/adamholsinger/mcp-servers/claude-local

echo "Testing claude command in container..."
docker run --rm \
  -v "$HOME/.claude:/home/node/.claude:rw" \
  -v "/tmp/npm-global-link:/host-npm-global:ro" \
  claude-container-claude-local \
  /bin/bash -c "
    echo '=== Environment ==='
    echo \"USER: \$USER\"
    echo \"HOME: \$HOME\"
    echo \"CLAUDE_CONFIG_DIR: \$CLAUDE_CONFIG_DIR\"
    echo
    echo '=== Claude location ==='
    which claude
    echo
    echo '=== Claude version ==='
    claude --version
    echo
    echo '=== .claude directory ==='
    ls -la /home/node/.claude/ | head -5
    echo
    echo '=== Checking API key ==='
    if [ -f /home/node/.claude/config.json ]; then
      echo 'config.json exists'
      # Check if API key is present (without showing it)
      grep -q 'apiKey' /home/node/.claude/config.json && echo 'API key found in config' || echo 'No API key in config'
    else
      echo 'No config.json found'
    fi
  "