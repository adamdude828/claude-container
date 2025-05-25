#!/bin/bash

# Test script for git env fix
cd /Users/adamholsinger/mcp-servers/claude-local/simple-test

# Create test inputs
cat << 'EOF' | claude-container task start
git-env-fix
Test git ownership fix with env vars
EOF