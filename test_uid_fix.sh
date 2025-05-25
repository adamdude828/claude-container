#!/bin/bash

# Test script for UID/GID fix
cd /Users/adamholsinger/mcp-servers/claude-local/simple-test

# Create test inputs
cat << 'EOF' | claude-container task start
uid-fix-test
Test git ownership with matching UID/GID
EOF