# Claude Container PR Workflow Plan

## Overview
Modify the daemon to create GitHub PRs upfront when tasks are submitted, then execute Claude Code within that PR's branch context.

## Workflow Sequence

```
1. Daemon Start → Check gh CLI
2. Task Submit → Create Branch → Create PR → Get PR URL
3. Container Run → Switch Branch → Pull → Execute Claude → Commit
```

## Implementation Plan

### 1. Daemon Startup Changes

#### 1.1 GitHub CLI Validation
```python
# In TaskDaemon.__init__ or start()
def validate_github_cli(self):
    """Check if gh CLI is installed and authenticated"""
    try:
        result = subprocess.run(['gh', 'auth', 'status'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                "GitHub CLI (gh) is required and must be authenticated.\n"
                "Install: https://cli.github.com/\n"
                "Authenticate: gh auth login"
            )
    except FileNotFoundError:
        raise RuntimeError(
            "GitHub CLI (gh) is not installed.\n"
            "Install: https://cli.github.com/"
        )
```

### 2. Task Submission Flow

#### 2.1 Modified Task Creation
```python
# In daemon submit handler
def submit_task(self, command, project_dir):
    # 1. Generate branch name
    task_id = str(uuid.uuid4())[:8]
    branch_name = f"claude-task-{task_id}"
    
    # 2. Create branch in project directory
    os.chdir(project_dir)
    subprocess.run(['git', 'checkout', '-b', branch_name])
    subprocess.run(['git', 'push', '-u', 'origin', branch_name])
    
    # 3. Create PR immediately
    pr_result = subprocess.run([
        'gh', 'pr', 'create',
        '--title', f'Claude Task: {command[:50]}...',
        '--body', f'Task ID: {task_id}\nCommand: {command}\n\nIn progress...',
        '--draft'  # Start as draft
    ], capture_output=True, text=True)
    
    pr_url = pr_result.stdout.strip()
    
    # 4. Store task with branch and PR info
    task = {
        'id': task_id,
        'command': command,
        'branch': branch_name,
        'pr_url': pr_url,
        'status': 'pending'
    }
    
    return task
```

### 3. Container Execution Wrapper

#### 3.1 Claude Code Wrapper Script
Create a wrapper script that runs inside the container:

```bash
#!/bin/bash
# claude-wrapper.sh

BRANCH_NAME=$1
shift  # Remove branch name from arguments

# Switch to the branch
git checkout $BRANCH_NAME

# Pull latest changes
git pull origin $BRANCH_NAME

# Run claude code with remaining arguments
claude-code "$@"

# Commit any changes
if [[ -n $(git status -s) ]]; then
    git add -A
    git commit -m "Claude task update on branch $BRANCH_NAME"
    git push origin $BRANCH_NAME
fi
```

#### 3.2 Modified Container Execution
```python
# In ContainerRunner or TaskDaemon
def execute_task_in_container(self, task):
    # Copy wrapper script to container
    wrapper_content = self.get_wrapper_script()
    
    command = [
        '/bin/bash', '-c',
        f'echo "{wrapper_content}" > /tmp/claude-wrapper.sh && '
        f'chmod +x /tmp/claude-wrapper.sh && '
        f'/tmp/claude-wrapper.sh {task["branch"]} {task["command"]}'
    ]
    
    # Run container with the wrapper
    container = self.docker_client.containers.run(
        image=self.image_name,
        command=command,
        volumes=self._get_volumes(),
        environment=self._get_environment(task),
        working_dir='/workspace',
        detach=True
    )
    
    return container
```

### 4. Task Lifecycle

#### 4.1 Task States with PR
```
SUBMITTED → BRANCH_CREATED → PR_CREATED → RUNNING → COMMITTING → COMPLETED
```

#### 4.2 Status Updates
- Update PR description as task progresses
- Mark PR as ready for review when task completes
- Add comments for significant milestones

### 5. File Structure Changes

```
claude_container/
├── core/
│   ├── task_daemon.py          # Add gh validation
│   ├── github_integration.py   # New: GitHub operations
│   └── wrapper_scripts.py      # New: Container scripts
└── models/
    └── task.py                 # Add branch, pr_url fields
```

### 6. Configuration

```yaml
# .claude-container/config.yaml
github:
  default_base_branch: main
  pr_options:
    draft: true  # Start as draft
    auto_ready: true  # Mark ready when complete
    delete_branch_on_merge: true
```

### 7. Error Handling

#### 7.1 Pre-execution Checks
- Verify clean git state before creating branch
- Check for existing branch names
- Ensure we're in a git repository

#### 7.2 Failure Scenarios
- Git operations fail → Abort task
- PR creation fails → Abort task, cleanup branch
- Container execution fails → Update PR with error

### 8. User Experience

```bash
# Start daemon (checks gh)
$ claude-container daemon start
✓ GitHub CLI authenticated
✓ Daemon started on port 8080

# Submit task
$ claude-container daemon submit "add error handling to API"
Creating branch: claude-task-a1b2c3d4
Creating pull request...
✓ PR created: https://github.com/user/repo/pull/42
✓ Task submitted: a1b2c3d4

# Check status
$ claude-container daemon status a1b2c3d4
Task: a1b2c3d4
Status: RUNNING
Branch: claude-task-a1b2c3d4
PR: https://github.com/user/repo/pull/42
```

### 9. MVP Implementation Steps

1. **Add gh CLI check to daemon startup**
2. **Create branch/PR on task submission**
3. **Pass branch name to container**
4. **Create wrapper script for git operations**
5. **Update task model to track PR info**
6. **Test with simple Claude commands**

### 10. Future Enhancements
- PR comment updates during execution
- Attach Claude's output as PR comments
- Support for updating existing PRs
- Branch protection rule compliance
- Multi-commit support with meaningful messages