# Task Start Command Issues

## Overview
This document tracks the issues discovered when running `claude-container task start` command and their current status.

## Fixed Issues

### 1. Syntax Error in task_daemon.py ✅
**Status:** Fixed  
**Description:** An `elif` statement was incorrectly placed after an `except` block, causing a syntax error when the daemon tried to start.  
**Solution:** Moved the `elif` block to be part of the original `if` statement inside the try block.

### 2. UnboundLocalError for pr_number variable ✅
**Status:** Fixed  
**Description:** The `pr_number` variable was being accessed outside the scope where it was defined due to incorrect indentation.  
**Error:**
```
UnboundLocalError: cannot access local variable 'pr_number' where it is not associated with a value
```
**Solution:** Fixed the indentation to ensure `pr_number` is only accessed within the scope where it's defined.

### 3. Command Quoting Issue ✅
**Status:** Fixed  
**Description:** The Claude prompt was being incorrectly passed to the wrapper script, causing the shell to interpret parts of the prompt as commands.  
**Solution:** Fixed by using `shlex.quote()` to properly escape shell arguments in task_daemon.py

## Remaining Issues

### 1. Git Repository Not in Mounted Directory ❌
**Status:** Root cause identified
**Description:** The Docker container cannot find the git repository because only a subdirectory is being mounted.
**Error Manifestation:**
```
fatal: not a git repository (or any parent up to mount point /)
Stopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).
```
**Debug Output:**
```
Current directory: /workspace
Checking for .git directory:
.git directory not found
```
**Root Cause:** The `simple-test` directory is mounted to `/workspace`, but the `.git` directory is in the parent directory `/Users/adamholsinger/mcp-servers/claude-local`. The container only has access to the subdirectory, not the git repository.
**Solution Needed:** Mount the git repository root directory instead of just the subdirectory, or initialize git repos within individual project directories.

### 2. Claude Code Not Found ❌
**Status:** Not Fixed  
**Description:** The `claude-code` command is not available in the Docker container.  
**Error Manifestation:**
```
Running Claude Code...
Error: Claude Code not found in mounted npm global directory
```
**Root Cause:** The claude-code binary is not being properly mounted or made available in the container's PATH.

### 3. PR Creation Failure ❌
**Status:** Not Fixed (Secondary Issue)  
**Description:** PR creation fails when there are no commits between master and the new branch.  
**Error Manifestation:**
```
Warning: 37 uncommitted changes
pull request create failed: GraphQL: No commits between master and test-branch-1748148352 (createPullRequest)
```
**Note:** This is a secondary issue that occurs because the task fails before making any commits.

## Testing Details

### Test Command Used
```bash
#!/bin/bash
echo "Testing task:start command with automatic inputs"
cd /Users/adamholsinger/mcp-servers/claude-local
echo -e "test-branch-$(date +%s)\nTest task description" | claude-container task start
```

### Daemon Logs Location
- Output: `/Users/adamholsinger/.claude-container/daemon.log`
- Errors: `/Users/adamholsinger/.claude-container/daemon.error.log`

### Successful Operations
1. Daemon starts successfully
2. Branch creation works
3. Branch push to remote works
4. Task submission to daemon works
5. Docker container creation works
6. Task execution starts

### Failed Operations
1. Git operations in container fail due to ownership issues
2. Claude command execution fails due to binary not found
3. Shell script parsing fails due to improper quoting
4. PR creation fails due to no commits

## Next Steps

1. ~~Fix command quoting in `task_daemon.py` to properly escape the command arguments~~ ✅
2. Investigate alternative approaches for Git ownership issues:
   - Consider running container with same UID/GID as host user
   - Look into Docker's userns-remap feature
   - Try mounting .gitconfig from host with safe.directory pre-configured
3. Ensure claude-code binary is properly mounted or installed in the container
4. Consider making PR creation optional or handling the "no commits" case gracefully