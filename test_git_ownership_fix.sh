#!/bin/bash

# Test script for git ownership fix
cd /Users/adamholsinger/mcp-servers/claude-local/simple-test

# Create test inputs
cat << 'EOF' | claude-container task start
test-git-ownership
Test git ownership fix in Docker container
EOF