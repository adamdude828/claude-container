#!/bin/bash

# Test script for UID/GID fix with simplified git
cd /Users/adamholsinger/mcp-servers/claude-local/simple-test

# Create test inputs
cat << 'EOF' | claude-container task start
uid-simple-test
Test git with UID fix and simplified commands
EOF