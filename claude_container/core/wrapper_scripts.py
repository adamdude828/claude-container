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

# Check if .claude directory is mounted correctly
echo "DEBUG: Checking .claude mount:"
ls -la /home/node/.claude/ | head -5

# Create a very permissive settings.json that allows all tools
cat > /home/node/.claude/settings.json << 'EOF'
{
  "permissions": {
    "allow": [
      "Bash(*)",
      "Read(*)",
      "Write(*)",
      "Edit(*)",
      "MultiEdit(*)",
      "Glob(*)",
      "Grep(*)",
      "LS(*)",
      "NotebookRead(*)",
      "NotebookEdit(*)",
      "WebFetch(*)",
      "WebSearch(*)",
      "TodoRead(*)",
      "TodoWrite(*)",
      "Task(*)"
    ],
    "deny": []
  }
}
EOF

# Run claude code with remaining arguments  
echo "Running Claude Code..."
echo "DEBUG: Number of arguments: $#"
echo "DEBUG: First few args:"
echo "  \$1: $1"
echo "  \$2: $2"
echo "  \$3: $(echo "$3" | head -c 100)..."

# Try running claude-code directly with the npm global path
if [ -f "/host-npm-global/lib/node_modules/@anthropic-ai/claude-code/cli.js" ]; then
    exec node /host-npm-global/lib/node_modules/@anthropic-ai/claude-code/cli.js "$@"
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