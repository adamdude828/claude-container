#!/bin/bash

# Test script for the task start command

echo "Testing claude-container task start command..."
echo ""
echo "This will:"
echo "1. Prompt for a branch name"
echo "2. Create a git branch"
echo "3. Create a GitHub PR using gh CLI"
echo ""
echo "Prerequisites:"
echo "- Must be in a git repository"
echo "- Must have gh CLI installed and authenticated"
echo ""

# Run the command
claude-container task start