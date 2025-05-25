#!/bin/bash

# Test script for git ownership fix v2
cd /Users/adamholsinger/mcp-servers/claude-local/simple-test

# Create test inputs
cat << 'EOF' | claude-container task start
git-fix-v2
Test git ownership fix v2
EOF