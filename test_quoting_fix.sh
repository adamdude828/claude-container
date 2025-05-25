#!/bin/bash

# Test script for command quoting fix
cd /Users/adamholsinger/mcp-servers/claude-local/simple-test

# Create test inputs with special characters
cat << 'EOF' | claude-container task start
test-quoting-fix
Fix the "special characters" issue (with quotes & parens)
EOF