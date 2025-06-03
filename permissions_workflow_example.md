# Claude Container Permissions Workflow

## Overview

The Claude Container now uses the `--dangerously-skip-permissions` flag instead of the liberal permissions JSON file approach. This provides a cleaner and more secure way to handle permissions.

## Changes Made

1. **Removed liberal permissions approach**:
   - Removed `LIBERAL_SETTINGS_JSON` from constants.py
   - Added `CLAUDE_SKIP_PERMISSIONS_FLAG` and `CLAUDE_PERMISSIONS_ERROR` constants

2. **Added new command**: `claude-container accept-permissions`
   - Runs Claude interactively to accept the `--dangerously-skip-permissions` flag
   - Checks if permissions are already accepted
   - Can force re-acceptance with `--force` flag

3. **Updated task commands**:
   - `task create` now checks if permissions are accepted before running
   - `task continue` also checks permissions
   - Both commands use the `--dangerously-skip-permissions` flag when invoking Claude

## Workflow

1. **First time setup**:
   ```bash
   # Build container
   claude-container build
   
   # Login to Claude
   claude-container login
   
   # Accept permissions
   claude-container accept-permissions
   ```

2. **Creating a task**:
   ```bash
   # Create a new task
   claude-container task create
   ```
   
   If permissions haven't been accepted, you'll see:
   ```
   ❌ Claude permissions have not been accepted yet.
   Please run 'claude-container accept-permissions' first.
   ```

3. **Continuing a task**:
   ```bash
   # Continue an existing task
   claude-container task continue <task-id>
   ```
   
   Same permission check applies.

## Technical Details

- The permission check runs: `claude -p "echo test" --dangerously-skip-permissions`
- If it fails with the specific error message about accepting permissions, we know permissions need to be accepted
- The accept-permissions command runs Claude interactively so the user can accept the flag
- Once accepted, all subsequent non-interactive Claude invocations will work with the flag

## Benefits

1. **Cleaner approach**: No need to manage settings.local.json files
2. **More secure**: Uses Claude's built-in permission system
3. **Better user experience**: Clear error messages and dedicated command
4. **Simpler codebase**: Less code to maintain