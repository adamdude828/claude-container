# Task Start Implementation Fix Plan

## Current State Analysis

### What's Working
1. Authentication check before starting tasks
2. Interactive prompts for branch name and task description
3. Basic git operations (checkout, commit, push)
4. PR creation using gh CLI
5. Container cleanup after task completion
6. Synchronous execution (as intended for v1)

### What's Broken/Missing
1. **Path Issues**: Using `/root/` paths instead of `/home/node/` for Claude files
2. **Not Using Unified Configuration**: Direct docker_client usage instead of ContainerRunner
3. **Missing Environment Variables**: Not setting NODE_OPTIONS, HOME properly
4. **Volume Mount Inconsistencies**: Not using the standardized volume mount configuration
5. **Error Handling**: Git operations need better error handling
6. **Container Name**: No proper naming for debugging/tracking
7. **Working Directory**: Not using DEFAULT_WORKDIR constant

## Implementation Plan

### Phase 1: Refactor to Use ContainerRunner (Priority: High) ✅ COMPLETED
**File: `claude_container/cli/commands/task.py`**
- ✅ Line 9: Imported ContainerRunner from `claude_container/core/container_runner.py`
- ✅ Lines 37-41: Replaced DockerClient initialization with ContainerRunner
- ✅ Lines 62-68: Removed manual volume mount configuration
- ✅ Line 67: Using container_runner.create_persistent_container() instead of manual container.run()
- ✅ Added DEFAULT_WORKDIR import and replaced all hardcoded "/workspace" references

**File: `claude_container/core/container_runner.py`**
- ✅ Lines 340-356: Added create_persistent_container() method to support task workflow

### Phase 2: Fix Volume Mounts and Paths ✅ COMPLETED
**File: `claude_container/cli/commands/task.py`**
- ✅ Lines 62-68: Manual volume definitions removed (now using ContainerRunner's _get_volumes())
- ✅ Environment variables automatically set correctly via ContainerRunner's _get_container_environment()

**Verification:**
- ContainerRunner._get_volumes() (lines 222-261) correctly mounts all paths to `/home/node/`
- ContainerRunner._get_container_environment() (lines 24-40) correctly sets:
  - CLAUDE_CONFIG_DIR: '/home/node/.claude'
  - HOME: '/home/node'
- create_persistent_container() uses both methods via _get_container_config()

### Phase 3: Improve Git Operations
**File: `claude_container/cli/commands/task.py`**
- Lines 88-112: Enhance git checkout logic with better error handling
- Lines 132-154: Improve commit handling
- Lines 156-165: Add retry logic for push operations
- Consider adding git config setup similar to `claude_container/core/task_daemon.py` (lines 194-208)

### Phase 4: Enhanced Error Handling
**File: `claude_container/cli/commands/task.py`**
- Lines 119-127: Add proper error capture for Claude execution
- Lines 88-106: Better branch checkout error messages
- Lines 144-154: More detailed commit failure reasons
- Add progress indicators throughout long operations

### Phase 5: Testing & Validation
**Files to create/modify:**
- `tests/cli/commands/test_task.py` - Add comprehensive tests
- `test_task_command.sh` - Update manual test script

## Specific File Changes

### `claude_container/cli/commands/task.py`
1. **Import section (lines 1-11)**
   - Add: `from ...core.container_runner import ContainerRunner`
   - Remove: Direct docker client usage

2. **start() function refactor (lines 20-211)**
   - Replace docker_client initialization (lines 35-39) with ContainerRunner
   - Remove manual volume configuration (lines 62-68)
   - Replace container.run() (lines 75-86) with ContainerRunner methods
   - Update all exec_run calls to use ContainerRunner's execution methods
   - Fix environment variables to use /home/node paths

3. **Git operations enhancement**
   - Add git identity setup before operations
   - Better error messages for common git failures
   - Handle force push scenarios

### `claude_container/core/container_runner.py`
- No changes needed - already has correct configuration
- _get_volumes() (lines 222-261) already uses /home/node paths
- _get_container_environment() (lines 24-40) already sets correct env vars

### `claude_container/core/constants.py`
- Verify DEFAULT_WORKDIR is used consistently

## Testing Checklist
1. **Authentication Flow**
   - File: `claude_container/cli/commands/task.py` line 24
   - Verify auth check works with new paths

2. **Git Operations**
   - New branch creation
   - Existing branch checkout
   - Empty commit handling
   - Push to remote

3. **Claude Execution**
   - Task execution with proper environment
   - Output streaming
   - Error handling

4. **PR Creation**
   - File: `claude_container/cli/commands/task.py` lines 167-194
   - Verify gh CLI integration

## Dependencies
- `claude_container/core/container_runner.py` - Main dependency for refactor
- `claude_container/core/docker_client.py` - Will be used indirectly through ContainerRunner
- `claude_container/core/constants.py` - For consistent paths/prefixes