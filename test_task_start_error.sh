#!/bin/bash

echo "Testing task start to see exact error message..."
echo "=============================================="

# Make sure daemon is running
poetry run claude-container daemon status

# Try to start a task and capture the exact error
echo -e "\nStarting task...\n"
echo -e "test-branch\nTest task description" | poetry run claude-container task start

echo -e "\n\nChecking daemon logs for error details..."
# Get the most recent task ID
TASK_ID=$(poetry run claude-container task list | grep -E "^  - " | tail -1 | awk '{print $2}' | sed 's/://')

if [ ! -z "$TASK_ID" ]; then
    echo "Getting output for task: $TASK_ID"
    poetry run claude-container task output "$TASK_ID"
fi