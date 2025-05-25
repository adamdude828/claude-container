#!/bin/bash

# Test script for git root fix
cd /Users/adamholsinger/mcp-servers/claude-local/simple-test

# Create test inputs
cat << 'EOF' | claude-container task start
git-root-fix
Test git operations with repository root mounting
EOF