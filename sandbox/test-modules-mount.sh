#!/bin/bash
echo "=== Testing Node Modules Mount ==="
echo ""
echo "User: $(whoami)"
echo "Home: $HOME"
echo ""

echo "Checking mounted node_modules:"
ls -la /host-node-modules/@anthropic-ai/ 2>/dev/null || echo "Claude Code not found in @anthropic-ai"
echo ""

if [ -d "/host-node-modules/@anthropic-ai/claude-code" ]; then
    echo "Found Claude Code package"
    
    # Create symlink in user's local bin
    echo "Creating local bin directory..."
    mkdir -p /home/node/.local/bin
    ln -sf /host-node-modules/@anthropic-ai/claude-code/cli.js /home/node/.local/bin/claude
    export PATH="/home/node/.local/bin:$PATH"
    
    echo ""
    echo "Testing claude --version:"
    claude --version 2>&1 || echo "Failed with exit code: $?"
    
    echo ""
    echo "Checking node compatibility:"
    node --version
    
    echo ""
    echo "Direct node execution test:"
    node /host-node-modules/@anthropic-ai/claude-code/cli.js --version 2>&1 || echo "Direct execution failed"
    
    echo ""
    echo "Environment:"
    env | grep -E "(CLAUDE|NODE|PATH)" | sort
    
    echo ""
    echo "Testing API authentication:"
    claude -p "Hello, testing auth" --model=opus 2>&1 || echo "API call failed with exit code: $?"
else
    echo "Claude Code package not found"
fi
