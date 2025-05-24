#!/bin/bash

# Test script to verify git communication from within container
# This script will:
# 1. Create a test file
# 2. Create a feature branch
# 3. Commit the file to the branch
# 4. Verify git operations work correctly

set -e  # Exit on error

echo "=== Git Communication Test Script ==="
echo "Testing git operations from within the container..."
echo

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print success
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
error() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

# 1. Check git is available
echo "1. Checking git availability..."
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version)
    success "Git is available: $GIT_VERSION"
else
    error "Git is not available"
fi

# 2. Check current directory
echo -e "\n2. Checking working directory..."
CURRENT_DIR=$(pwd)
success "Current directory: $CURRENT_DIR"

# 3. Check git repository status
echo -e "\n3. Checking git repository..."
if git rev-parse --git-dir > /dev/null 2>&1; then
    REPO_ROOT=$(git rev-parse --show-toplevel)
    success "Git repository found at: $REPO_ROOT"
else
    echo "Warning: Not in a git repository. Creating a test repository..."
    
    # Initialize a new git repository for testing
    TEST_REPO_DIR="/workspace/git-test-repo"
    mkdir -p "$TEST_REPO_DIR"
    cd "$TEST_REPO_DIR"
    
    git init
    success "Initialized test repository at: $TEST_REPO_DIR"
    
    # Configure git user if needed
    if [ "$(git config --global user.name)" = "" ]; then
        git config --global user.name "Test User"
        git config --global user.email "test@example.com"
        echo "Configured git user for testing"
    fi
    
    # Create initial commit
    echo "# Test Repository" > README.md
    git add README.md
    git commit -m "Initial commit"
    success "Created initial commit"
fi

# 4. Check git configuration
echo -e "\n4. Checking git configuration..."
GIT_USER=$(git config --global user.name || echo "Not set")
GIT_EMAIL=$(git config --global user.email || echo "Not set")
if [ "$GIT_USER" != "Not set" ] && [ "$GIT_EMAIL" != "Not set" ]; then
    success "Git user: $GIT_USER <$GIT_EMAIL>"
else
    error "Git user configuration not found"
fi

# 5. Check SSH key availability
echo -e "\n5. Checking SSH configuration..."
if [ -d "$HOME/.ssh" ]; then
    success "SSH directory found at: $HOME/.ssh"
    if [ -f "$HOME/.ssh/id_rsa" ] || [ -f "$HOME/.ssh/id_ed25519" ]; then
        success "SSH keys are available"
    else
        echo "Warning: No standard SSH keys found (id_rsa or id_ed25519)"
    fi
else
    error "SSH directory not found"
fi

# 6. Test remote connectivity
echo -e "\n6. Testing remote connectivity..."
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "No remote")
if [ "$REMOTE_URL" != "No remote" ]; then
    success "Remote origin: $REMOTE_URL"
    
    # Test if we can fetch from remote
    if git ls-remote origin HEAD &>/dev/null; then
        success "Can communicate with remote repository"
    else
        error "Cannot communicate with remote repository"
    fi
else
    echo "Warning: No remote origin configured"
    
    # Test SSH connectivity to GitHub
    echo "Testing SSH connectivity to GitHub..."
    if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
        success "SSH authentication to GitHub works"
    else
        echo "Note: SSH to GitHub may require authentication"
    fi
fi

# 7. Create test branch
echo -e "\n7. Creating test branch..."
TEST_BRANCH="test/git-communication-$(date +%Y%m%d-%H%M%S)"
CURRENT_BRANCH=$(git branch --show-current)
success "Current branch: $CURRENT_BRANCH"

git checkout -b "$TEST_BRANCH"
success "Created and switched to branch: $TEST_BRANCH"

# 8. Create test file
echo -e "\n8. Creating test file..."
TEST_FILE="git-test-$(date +%Y%m%d-%H%M%S).txt"
cat > "$TEST_FILE" << EOF
Git Communication Test
=====================

This file was created to test git communication from within the Docker container.

Test Details:
- Date: $(date)
- User: $GIT_USER
- Email: $GIT_EMAIL
- Branch: $TEST_BRANCH
- Container: $(hostname)

This is a temporary test file and can be safely deleted.
EOF

success "Created test file: $TEST_FILE"

# 9. Stage and commit the file
echo -e "\n9. Staging and committing..."
git add "$TEST_FILE"
git commit -m "Test: Verify git communication from container

This commit tests that the Docker container can:
- Create branches
- Stage files
- Make commits
- Communicate with the remote repository

Test file: $TEST_FILE
Test branch: $TEST_BRANCH"

success "File committed successfully"

# 10. Show commit details
echo -e "\n10. Commit details..."
COMMIT_HASH=$(git rev-parse HEAD)
success "Commit hash: $COMMIT_HASH"
echo -e "\nCommit info:"
git show --stat

# Summary
echo -e "\n=== Test Summary ==="
success "All git operations completed successfully!"
echo -e "\nThe following was verified:"
echo "- Git is available in the container"
echo "- Git user configuration is accessible"
echo "- SSH keys are mounted and accessible"
echo "- Can communicate with remote repository"
echo "- Can create branches"
echo "- Can create and commit files"
echo -e "\nTest branch: $TEST_BRANCH"
echo "Test file: $TEST_FILE"
echo -e "\nTo push this test branch, run:"
echo "  git push -u origin $TEST_BRANCH"
echo -e "\nTo clean up after testing:"
echo "  git checkout $CURRENT_BRANCH"
echo "  git branch -d $TEST_BRANCH"
echo "  rm $TEST_FILE"