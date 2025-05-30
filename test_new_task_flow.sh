#!/bin/bash

# Test script for new task flow
set -e

echo "Testing new task flow with feature branch creation..."
echo "======================================================="

# Ensure we're in a test project
cd simple-test || {
    echo "Error: simple-test directory not found"
    exit 1
}

# Initialize git if needed
if [ ! -d .git ]; then
    git init
    git add .
    git commit -m "Initial commit"
fi

echo ""
echo "Starting task command test..."
echo "When prompted:"
echo "  - Enter a task description (e.g., 'Add error handling to index.js')"
echo ""

# Run the task start command
../dist/claude-container task start

echo ""
echo "Test complete! Check the output above for:"
echo "1. Feature branch creation (feature/your-task-name)"
echo "2. First Claude run executing the task"
echo "3. Second Claude run committing changes"
echo "4. PR creation attempt"