# Task Storage System Design

Based on my analysis of the codebase, here's a comprehensive plan for implementing persistent task storage:

## Current State Analysis

The existing system runs tasks **ephemerally** - containers are created, execute the task, then are removed. Task tracking currently happens only through:
- Active Docker containers (listed via `task list`)
- Git branches and pull requests
- No persistent task metadata storage

## Proposed Task Storage Architecture

### 1. Storage Location & Structure

**Location**: Extend the existing `.claude-container/` directory pattern
```
project-root/
├── .claude-container/
│   ├── container_config.json          # existing
│   ├── Dockerfile.claude              # existing  
│   └── tasks/                         # NEW: task storage
│       ├── task_registry.json         # master task list
│       ├── tasks/
│       │   ├── {task-id}/
│       │   │   ├── metadata.json      # task details
│       │   │   ├── feedback/          # feedback history
│       │   │   │   ├── 001_initial.md
│       │   │   │   ├── 002_continue.md
│       │   │   │   └── 003_continue.md
│       │   │   └── logs/
│       │   │       ├── claude_output.log
│       │   │       └── execution.log
│       │   └── {task-id-2}/
│       └── templates/                 # task templates (future)
```

### 2. Data Models

**Task Status Enum**:
- `created` - Task created with PR
- `continued` - Task has been continued with feedback
- `failed` - Task encountered error

**Task Metadata Model**:
```python
@dataclass
class TaskMetadata:
    id: str                    # UUID
    description: str           # User-provided task description
    status: TaskStatus         # Current status
    branch_name: str           # Git branch name
    created_at: datetime       # When task was created
    started_at: Optional[datetime]     # When execution began
    completed_at: Optional[datetime]   # When execution finished
    container_id: Optional[str]        # Docker container ID (if running)
    pr_url: Optional[str]             # GitHub PR URL (if created)
    commit_hash: Optional[str]        # Git commit hash (if committed)
    error_message: Optional[str]      # Error details (if failed)
    feedback_history: List[FeedbackEntry] = []  # All feedback provided
    last_continued_at: Optional[datetime]  # When task was last continued
    continuation_count: int = 0            # Number of times continued

@dataclass
class FeedbackEntry:
    timestamp: datetime
    feedback: str
    feedback_type: str  # "text", "file", "inline"
    claude_response_summary: Optional[str]  # Brief summary of what Claude did
```

### 3. CLI Commands

#### 3.1 Task Create

**Command**: `claude-container task create`

```bash
# Interactive mode - opens editor for task description
claude-container task create
claude-container task create --branch auth-feature

# Non-interactive mode with file
claude-container task create --file task-description.md
claude-container task create --file task-description.md --branch auth-feature
```

**Workflow**:
- Open editor for task description (or read from --file)
- Prompt for branch name if not provided via --branch
- Create task record in storage
- Generate unique task ID
- Store initial task metadata and description
- Start Claude Code container with the task
- Execute task to completion
- Create GitHub PR automatically
- Stop and remove container
- Store PR URL in task metadata

#### 3.2 Task Continue

**Command**: `claude-container task continue <task-id-or-pr-url>`

```bash
# Continue with inline feedback string
claude-container task continue abc123 \
  --feedback "Make sure to add password strength validation"

# Continue with PR URL and feedback
claude-container task continue https://github.com/user/repo/pull/123 \
  --feedback "Address the review comments"

# Open editor for feedback (no --feedback provided)
claude-container task continue abc123

# Continue with a feedback file
claude-container task continue abc123 \
  --feedback-file ./additional-requirements.md
```

**Workflow**:
- Accept task ID or PR URL as identifier
- If PR URL provided, look up associated task
- For feedback: accepts inline string via --feedback, file via --feedback-file, or opens editor if neither provided
- Git checkout the task's branch
- Git pull to get latest changes
- Append new feedback to feedback history
- Start new Claude Code container
- Claude sees previous context + new feedback
- Update logs and metadata with continuation
- Increment continuation count
- Stop and remove container after completion

#### 3.3 Task List

**Command**: `claude-container task list`

```bash
# List all tasks with enhanced info
claude-container task list
claude-container task list --status created
```

- Shows both containers AND stored tasks
- Enhanced display with PR URLs and continuation count

#### 3.4 Task Show

**Command**: `claude-container task show <task-id>`

```bash
# Show detailed task information including feedback history
claude-container task show abc123
claude-container task show abc123 --feedback-history
```

#### 3.5 Task Delete

**Command**: `claude-container task delete <task-id>`

```bash
# Delete task and all associated data
claude-container task delete abc123
claude-container task delete --status failed  # bulk delete
```

#### 3.6 Task Logs

**Command**: `claude-container task logs <task-id>`

```bash
# View task execution logs
claude-container task logs abc123
claude-container task logs abc123 --follow  # live tail
claude-container task logs abc123 --feedback  # show feedback history
```

#### 3.7 Task History

**Command**: `claude-container task history`

```bash
# Show task execution history
claude-container task history --limit 10
claude-container task history --branch main
```

#### 3.8 Task Search

**Command**: `claude-container task search`

```bash
# Search tasks by description
claude-container task search "authentication"
```

### 4. Container and Workflow Details

**Container Lifecycle**:
- Containers are ephemeral - created for each create/continue operation
- No persistent containers between operations
- All state preserved via git branches and task metadata

**Feedback Integration**:
- Each continuation adds to a feedback chain
- Claude can see full conversation history via task metadata
- Feedback is versioned and timestamped
- Support for both inline text and file-based feedback

### 5. Storage Manager Implementation

**New Class: `TaskStorageManager`**
```python
class TaskStorageManager:
    def __init__(self, data_dir: Path):
        self.tasks_dir = data_dir / "tasks"
        self.registry_file = self.tasks_dir / "task_registry.json"
    
    def create_task(self, description_file: Path, **kwargs) -> TaskMetadata
    def get_task(self, task_id: str) -> TaskMetadata
    def update_task(self, task_id: str, **updates) -> None
    def add_feedback(self, task_id: str, feedback: str, feedback_type: str) -> None
    def get_feedback_history(self, task_id: str) -> List[FeedbackEntry]
    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[TaskMetadata]
    def delete_task(self, task_id: str) -> None
    def search_tasks(self, query: str) -> List[TaskMetadata]
    def lookup_task_by_pr(self, pr_url: str) -> Optional[TaskMetadata]
    def create_pr_for_task(self, task_id: str) -> str
```

### 6. Integration Points

**With Existing Commands**:
- `clean` - Option to clean task storage data
- `config` - Add task-related configuration options

**With External Systems**:
- **Git Integration**: Track branch associations and commit hashes
- **GitHub Integration**: Store PR URLs and status updates
- **Docker Integration**: Link running containers to task records

### 7. Advanced Features (Future)

**Task Templates**:
```bash
claude-container task template create "bug-fix" \
  --description "Fix bug: {issue}" \
  --branch "bugfix/{issue-number}"
```

**Task Dependencies**:
```bash
claude-container task create "Deploy feature" \
  --depends-on abc123  # wait for task abc123 to complete
```

**Scheduled Tasks**:
```bash
claude-container task schedule "Weekly cleanup" \
  --cron "0 0 * * 0"
```

## Implementation Strategy

1. **Phase 1**: Basic storage system and core commands (`create`, `continue`, `list`, `show`, `delete`)
2. **Phase 2**: Enhanced feedback workflow with PR integration and logging
3. **Phase 3**: Search and history features (`search`, `history`)


This design maintains backward compatibility while adding powerful task management capabilities that persist beyond container lifecycles.