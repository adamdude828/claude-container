#!/bin/bash

# Test script to debug workspace
cd /Users/adamholsinger/mcp-servers/claude-local/simple-test

# Create test inputs
cat << 'EOF' | claude-container task start
debug-workspace
Debug workspace and git directory
EOF