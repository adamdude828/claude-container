#!/bin/bash
echo "=== Testing Anthropic Dev Container ==="
echo ""
echo "User: $(whoami)"
echo "Home: $HOME"
echo "Working directory: $(pwd)"
echo ""

echo "Environment variables:"
env | grep -E "(CLAUDE|NODE_OPTIONS|NPM)" | sort
echo ""

echo "Checking .claude directory:"
ls -la ~/.claude/
echo ""

echo "Checking .claude.json file:"
if [ -f ~/.claude.json ]; then
    echo "✓ .claude.json exists"
    echo "File permissions: $(ls -la ~/.claude.json)"
    echo "File size: $(wc -c < ~/.claude.json) bytes"
    echo "Can read file: $(if cat ~/.claude.json > /dev/null 2>&1; then echo 'Yes'; else echo 'No'; fi)"
else
    echo "✗ .claude.json not found"
fi
echo ""

echo "Installing Claude Code..."
npm install -g @anthropic-ai/claude-code
echo ""

echo "Claude Code version:"
claude --version
echo ""

echo "Testing Claude with simple prompt:"
echo "First, let's check if Claude can find the config:"
claude --version --verbose 2>&1 || true
echo ""

echo "Checking API key in claude.json:"
if grep -q "apiKey" ~/.claude.json; then
    echo "✓ apiKey field found in .claude.json"
else
    echo "✗ apiKey field not found in .claude.json"
fi
echo ""

echo "Current CLAUDE_CONFIG_DIR: $CLAUDE_CONFIG_DIR"
echo ""

echo "Let's check what's in the .claude config directory:"
ls -la $CLAUDE_CONFIG_DIR/
echo ""

echo "Is there a config.json in .claude directory?"
if [ -f "$CLAUDE_CONFIG_DIR/config.json" ]; then
    echo "✓ config.json exists in .claude directory"
    echo "Checking for apiKey in config.json:"
    if grep -q "apiKey" "$CLAUDE_CONFIG_DIR/config.json"; then
        echo "✓ apiKey found in config.json"
        echo "First few chars of apiKey in config.json:"
        grep "apiKey" "$CLAUDE_CONFIG_DIR/config.json" | head -1 | sed 's/.*"apiKey"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' | cut -c1-10
    else
        echo "✗ apiKey not found in config.json"
    fi
else
    echo "✗ config.json not found in .claude directory"
fi
echo ""

echo "For comparison, first few chars of apiKey in .claude.json:"
grep "apiKey" ~/.claude.json | head -1 | sed 's/.*"apiKey"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' | cut -c1-10 || echo "Could not extract apiKey"
echo ""

echo "Testing API call with model specified:"
claude -p "say hello" --model=opus 2>&1 || true
