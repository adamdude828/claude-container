#!/bin/bash
echo "Testing Claude Code authentication..."
echo ""
echo "Running: node /usr/local/lib/node_modules/@anthropic-ai/claude-code/cli.js -p 'say hello' --print"
node /usr/local/lib/node_modules/@anthropic-ai/claude-code/cli.js -p "say hello" --print

echo ""
echo "Exit code: $?"
