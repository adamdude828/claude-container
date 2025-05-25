#!/bin/bash

# Final test for git fix
cd /Users/adamholsinger/mcp-servers/claude-local/simple-test

# Create test inputs
cat << 'EOF' | claude-container task start
final-git-test
Test complete git workflow with all fixes
EOF