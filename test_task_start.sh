#!/bin/bash

echo "Testing task:start command with automatic inputs"

# Change to project directory
cd /Users/adamholsinger/mcp-servers/claude-local

# Provide inputs automatically
echo -e "test-branch-$(date +%s)\nTest task description" | claude-container task start