#!/bin/bash
# Debug Claude authentication

CLAUDE_CODE_DIR="/Users/adamholsinger/Library/Application Support/Herd/config/nvm/versions/node/v18.20.4/lib/node_modules/@anthropic-ai/claude-code"

# Create debug script
cat > debug-auth.sh << 'EOF'
#!/bin/bash
echo "=== Debugging Claude Auth ==="
echo ""

echo "1. Checking mounted files:"
echo "   ~/.claude.json exists: $([ -f /root/.claude.json ] && echo "Yes" || echo "No")"
echo "   ~/.claude dir exists: $([ -d /root/.claude ] && echo "Yes" || echo "No")"
echo ""

echo "2. File permissions:"
ls -la /root/.claude.json 2>/dev/null || echo "   .claude.json not found"
echo ""

echo "3. .claude.json size:"
wc -c /root/.claude.json 2>/dev/null || echo "   Can't read file"
echo ""

echo "4. Environment variables:"
env | grep -i claude || echo "   No CLAUDE env vars found"
echo ""

echo "5. Node.js can read the file:"
node -e "
const fs = require('fs');
try {
  const data = fs.readFileSync('/root/.claude.json', 'utf8');
  console.log('   File readable by Node.js: Yes');
  console.log('   File size:', data.length, 'bytes');
  console.log('   First 100 chars:', data.substring(0, 100) + '...');
} catch (e) {
  console.log('   Error reading file:', e.message);
}
"

echo ""
echo "6. Checking Claude Code dependencies:"
ls -la /usr/local/lib/node_modules/@anthropic-ai/claude-code/node_modules/ 2>/dev/null | head -5

echo ""
echo "7. Testing with explicit config path:"
echo "   Running: CLAUDE_CONFIG=/root/.claude.json node cli.js --version"
cd /usr/local/lib/node_modules/@anthropic-ai/claude-code
CLAUDE_CONFIG=/root/.claude.json node cli.js --version

echo ""
echo "8. Checking home directory:"
echo "   HOME=$HOME"
echo "   whoami: $(whoami)"
EOF

chmod +x debug-auth.sh

# Run debug
docker run --rm \
  -v "$(pwd)":/workspace \
  -v "$HOME/.claude.json":/root/.claude.json:rw \
  -v "$HOME/.claude":/root/.claude:rw \
  -v "$CLAUDE_CODE_DIR":/usr/local/lib/node_modules/@anthropic-ai/claude-code:ro \
  claude-mount-test \
  /workspace/debug-auth.sh