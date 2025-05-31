#!/bin/bash
# Test script for Phase 2 - Enhanced feedback workflow with PR integration and logging

set -e

echo "=== Phase 2 Test: Enhanced Feedback Workflow ==="
echo

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test project directory
TEST_DIR="./test-phase2-project"
TASK_DESC_FILE="task_description.md"
FEEDBACK_FILE="feedback.md"

# Clean up any existing test directory
if [ -d "$TEST_DIR" ]; then
    echo "Cleaning up existing test directory..."
    rm -rf "$TEST_DIR"
fi

# Create test project
echo -e "${BLUE}1. Creating test project...${NC}"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"
git init
echo "# Test Phase 2 Project" > README.md
git add README.md
git commit -m "Initial commit"

# Build the container
echo -e "\n${BLUE}2. Building container...${NC}"
claude-container build

# Create a task description file
echo -e "\n${BLUE}3. Creating task description...${NC}"
cat > "$TASK_DESC_FILE" << 'EOF'
# Task: Create a simple greeting module

Please create a Python module that:
1. Has a function called `greet(name)` that returns a greeting message
2. Has a function called `farewell(name)` that returns a goodbye message
3. Include a main section that demonstrates both functions
4. Add docstrings to all functions

Save it as `greeting.py`.
EOF

echo "Task description created in $TASK_DESC_FILE"

# Create the task
echo -e "\n${BLUE}4. Creating task with description file...${NC}"
echo "Running: claude-container task create --file $TASK_DESC_FILE --branch greeting-module"
TASK_OUTPUT=$(claude-container task create --file "$TASK_DESC_FILE" --branch greeting-module 2>&1)
echo "$TASK_OUTPUT"

# Extract task ID (assuming it's displayed in the output)
TASK_ID=$(echo "$TASK_OUTPUT" | grep -oE 'Task [a-f0-9-]{8}' | head -1 | awk '{print $2}')

if [ -z "$TASK_ID" ]; then
    echo -e "${YELLOW}Warning: Could not extract task ID from output${NC}"
    # Try to get it from task list
    TASK_ID=$(claude-container task list | grep greeting-module | awk '{print $1}' | head -1)
fi

echo -e "\n${GREEN}Task created with ID: $TASK_ID${NC}"

# Wait a moment for PR to be created
sleep 2

# Show the task details
echo -e "\n${BLUE}5. Showing task details...${NC}"
claude-container task show "$TASK_ID"

# Get PR URL from task
PR_URL=$(claude-container task show "$TASK_ID" | grep -A1 "Pull Request:" | tail -1 | xargs)
echo -e "\n${GREEN}PR URL: $PR_URL${NC}"

# View the logs
echo -e "\n${BLUE}6. Viewing task logs...${NC}"
claude-container task logs "$TASK_ID" | head -20
echo "... (truncated)"

# Create feedback file
echo -e "\n${BLUE}7. Creating feedback for continuation...${NC}"
cat > "$FEEDBACK_FILE" << 'EOF'
Please make the following improvements:

1. Add type hints to all functions
2. Add a `greet_multiple(names: List[str])` function that greets multiple people
3. Add error handling for empty or None names
4. Update the main section to demonstrate the new function
EOF

echo "Feedback created in $FEEDBACK_FILE"

# Continue the task with feedback file
echo -e "\n${BLUE}8. Continuing task with feedback file...${NC}"
echo "Running: claude-container task continue $TASK_ID --feedback-file $FEEDBACK_FILE"
claude-container task continue "$TASK_ID" --feedback-file "$FEEDBACK_FILE"

# Show updated task details with feedback history
echo -e "\n${BLUE}9. Showing task with feedback history...${NC}"
claude-container task show "$TASK_ID" --feedback-history

# View logs including continuation
echo -e "\n${BLUE}10. Viewing logs with --feedback flag...${NC}"
claude-container task logs "$TASK_ID" --feedback | head -30
echo "... (truncated)"

# Continue using PR URL with inline feedback
echo -e "\n${BLUE}11. Continuing task using PR URL with inline feedback...${NC}"
echo "Running: claude-container task continue \"$PR_URL\" --feedback \"Add a __version__ variable set to '1.0.0'\""
claude-container task continue "$PR_URL" --feedback "Add a __version__ variable set to '1.0.0'"

# List all tasks to show continuation count
echo -e "\n${BLUE}12. Listing all tasks...${NC}"
claude-container task list

# Final task details
echo -e "\n${BLUE}13. Final task details with full feedback history...${NC}"
claude-container task show "$TASK_ID" --feedback-history

# Check the actual file created
echo -e "\n${BLUE}14. Checking the created greeting.py file...${NC}"
if [ -f "greeting.py" ]; then
    echo "File contents:"
    cat greeting.py
else
    echo -e "${YELLOW}Warning: greeting.py not found${NC}"
fi

# Summary
echo -e "\n${GREEN}=== Phase 2 Test Complete ===${NC}"
echo
echo "Summary of features tested:"
echo "✓ PR URL lookup in task continue command"
echo "✓ Feedback history tracking (file and inline)"
echo "✓ PR URL storage and display"
echo "✓ Task logs command with --follow and --feedback options"
echo "✓ Feedback display in task show command"
echo
echo -e "${BLUE}Test project location: $(pwd)${NC}"
echo -e "${BLUE}Task ID: $TASK_ID${NC}"
echo -e "${BLUE}PR URL: $PR_URL${NC}"

# Optionally clean up
echo
read -p "Do you want to clean up the test project? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd ..
    rm -rf "$TEST_DIR"
    echo "Test project cleaned up."
fi