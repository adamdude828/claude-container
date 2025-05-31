# PR URL Storage Analysis for Claude Container Tasks

## Overview
This document analyzes how PR URLs are stored when creating tasks in the Claude Container system.

## Current Implementation

### 1. PR URL Storage in Task Metadata
The PR URL is stored as an optional field in the `TaskMetadata` model:
- **Location**: `claude_container/models/task.py` (line 35)
- **Field**: `pr_url: Optional[str] = None`

### 2. PR URL Creation and Storage Flow
When a task is created using `claude-container task create`:

1. **PR Creation** (lines 403-432 in `task.py`):
   - After Claude completes the task and commits changes
   - The system uses `gh pr create` command to create a draft PR
   - The PR URL is extracted from the command output

2. **Storage** (lines 428-431):
   ```python
   pr_url = pr_result.stdout.strip()
   if pr_url.startswith("https://"):
       storage_manager.update_task(task_metadata.id, pr_url=pr_url)
   ```

3. **Registry Update**:
   - The PR URL is also stored in the task registry (JSON file)
   - Updated via `TaskStorageManager.update_task()` method
   - Registry location: `.claude-container/tasks/task_registry.json`

### 3. PR URL Persistence
The PR URL is persisted in two places:
1. **Task Metadata File**: `.claude-container/tasks/tasks/{task_id}/metadata.json`
2. **Task Registry**: `.claude-container/tasks/task_registry.json`

### 4. PR URL Retrieval
PR URLs can be retrieved through:
1. **By Task ID**: Using `storage_manager.get_task(task_id)`
2. **By PR URL**: Using `storage_manager.lookup_task_by_pr(pr_url)` (line 312-327 in `task_storage.py`)
3. **In Task Listings**: Displayed with `[PR]` indicator in task list (line 159-160 in `task.py`)

## Key Features

### 1. PR URL Lookup
The system supports looking up tasks by their PR URL:
- Used in `claude-container task continue` command
- Allows continuation of tasks by providing the GitHub PR URL

### 2. GitHub Integration Module
While there's a `GitHubIntegration` class in `github_integration.py`, it's not currently used in the main task flow. The PR creation is done directly via subprocess calls to `gh` CLI.

## Enhancement Opportunities

1. **Automatic PR Updates**: The `GitHubIntegration` class has methods for updating PR descriptions and marking PRs as ready, but these aren't currently used in the task workflow.

2. **PR Status Tracking**: Could add fields to track PR status (draft/ready/merged) in the task metadata.

3. **PR Number Storage**: Currently only stores the full URL, could also extract and store the PR number for easier CLI operations.

4. **Integration with GitHub API**: Could use the GitHub API directly instead of relying on `gh` CLI for better error handling and richer PR metadata.

## Summary
PR URL storage is already implemented in the Claude Container system. When a task creates a PR, the URL is:
1. Captured from the `gh pr create` command output
2. Stored in the task metadata
3. Persisted to disk in both the task's metadata file and the registry
4. Available for lookup and display in various commands

The implementation is functional but could be enhanced with better GitHub integration and additional PR-related metadata tracking.