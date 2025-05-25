"""Wrapper scripts for container execution."""


def get_claude_wrapper_script() -> str:
    """Get the Claude wrapper script that handles git operations."""
    return '''#!/bin/bash
# Claude wrapper script for git operations

# Ensure PATH includes claude command location
export PATH="/home/node/.local/bin:$PATH"

# Set git environment variables to avoid config file issues
export GIT_AUTHOR_NAME="Claude Container"
export GIT_AUTHOR_EMAIL="claude@container.local"
export GIT_COMMITTER_NAME="Claude Container"
export GIT_COMMITTER_EMAIL="claude@container.local"

BRANCH_NAME=$1
shift  # Remove branch name from arguments

# Define git function with safe.directory config
git() {
    command git -c safe.directory=/workspace "$@"
}

# Switch to the branch
echo "Switching to branch: $BRANCH_NAME"
git checkout $BRANCH_NAME

# Pull latest changes
echo "Pulling latest changes..."
git pull origin $BRANCH_NAME

# Run claude code with remaining arguments  
echo "Running Claude Code..."
# Debug: show environment and config
echo "DEBUG: HOME=$HOME"
echo "DEBUG: CLAUDE_CONFIG_DIR=$CLAUDE_CONFIG_DIR"
echo "DEBUG: Checking .claude.json:"
cat /home/node/.claude.json 2>/dev/null | head -5 || echo "No .claude.json found"
echo "DEBUG: Running claude-code with args: $@"

# Try running claude-code directly with the npm global path
if [ -f "/host-npm-global/lib/node_modules/@anthropic-ai/claude-code/cli.js" ]; then
    node /host-npm-global/lib/node_modules/@anthropic-ai/claude-code/cli.js "$@"
    CLAUDE_EXIT_CODE=$?
else
    echo "ERROR: Claude Code CLI not found at expected path"
    CLAUDE_EXIT_CODE=1
fi

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

# Mark /workspace as a safe directory to handle ownership issues
git config --global --add safe.directory /workspace
'''