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
