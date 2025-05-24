"""Wrapper scripts for container execution."""


def get_claude_wrapper_script() -> str:
    """Get the Claude wrapper script that handles git operations."""
    return '''#!/bin/bash
# Claude wrapper script for git operations

# Ensure PATH includes claude command location
export PATH="/home/node/.local/bin:$PATH"

BRANCH_NAME=$1
shift  # Remove branch name from arguments

# Switch to the branch
echo "Switching to branch: $BRANCH_NAME"
git checkout $BRANCH_NAME

# Pull latest changes
echo "Pulling latest changes..."
git pull origin $BRANCH_NAME

# Run claude code with remaining arguments
echo "Running Claude Code..."
claude "$@"
CLAUDE_EXIT_CODE=$?

# Commit any changes
if [[ -n $(git status -s) ]]; then
    echo "Committing changes..."
    git add -A
    git commit -m "Claude task update on branch $BRANCH_NAME"
    
    echo "Pushing changes..."
    git push origin $BRANCH_NAME
else
    echo "No changes to commit."
fi

exit $CLAUDE_EXIT_CODE
'''


def get_git_config_script() -> str:
    """Get script to configure git in container."""
    return '''#!/bin/bash
# Configure git if not already configured
if [ -z "$(git config --global user.email)" ]; then
    git config --global user.email "claude@container.local"
fi

if [ -z "$(git config --global user.name)" ]; then
    git config --global user.name "Claude Container"
fi
'''