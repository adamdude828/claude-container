"""Task storage manager for persistent task tracking."""
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from claude_container.models.task import FeedbackEntry, TaskMetadata, TaskStatus


class TaskStorageManager:
    """Manages persistent storage of task metadata and history."""

    def __init__(self, data_dir: Path):
        """Initialize task storage manager.

        Args:
            data_dir: The .claude-container directory for the project
        """
        self.tasks_dir = data_dir / "tasks"
        self.registry_file = self.tasks_dir / "task_registry.json"
        self._ensure_storage_structure()

    def _ensure_storage_structure(self) -> None:
        """Ensure the storage directory structure exists."""
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        (self.tasks_dir / "tasks").mkdir(exist_ok=True)

        # Create registry file if it doesn't exist
        if not self.registry_file.exists():
            self._save_registry({})

    def _load_registry(self) -> dict:
        """Load the task registry from disk."""
        if self.registry_file.exists():
            with open(self.registry_file) as f:
                return json.load(f)
        return {}

    def _save_registry(self, registry: dict) -> None:
        """Save the task registry to disk."""
        with open(self.registry_file, 'w') as f:
            json.dump(registry, f, indent=2, sort_keys=True)

    def _get_task_dir(self, task_id: str) -> Path:
        """Get the directory for a specific task."""
        return self.tasks_dir / "tasks" / task_id

    def _serialize_task(self, task: TaskMetadata) -> dict:
        """Serialize a task to JSON-compatible dict."""
        return {
            "id": task.id,
            "description": task.description,
            "status": task.status.value,
            "branch_name": task.branch_name,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "container_id": task.container_id,
            "pr_url": task.pr_url,
            "commit_hash": task.commit_hash,
            "error_message": task.error_message,
            "feedback_history": [
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "feedback": entry.feedback,
                    "feedback_type": entry.feedback_type,
                    "claude_response_summary": entry.claude_response_summary
                }
                for entry in task.feedback_history
            ],
            "last_continued_at": task.last_continued_at.isoformat() if task.last_continued_at else None,
            "continuation_count": task.continuation_count
        }

    def _deserialize_task(self, data: dict) -> TaskMetadata:
        """Deserialize a task from JSON data."""
        return TaskMetadata(
            id=data["id"],
            description=data["description"],
            status=TaskStatus(data["status"]),
            branch_name=data["branch_name"],
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data["started_at"] else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data["completed_at"] else None,
            container_id=data.get("container_id"),
            pr_url=data.get("pr_url"),
            commit_hash=data.get("commit_hash"),
            error_message=data.get("error_message"),
            feedback_history=[
                FeedbackEntry(
                    timestamp=datetime.fromisoformat(entry["timestamp"]),
                    feedback=entry["feedback"],
                    feedback_type=entry["feedback_type"],
                    claude_response_summary=entry.get("claude_response_summary")
                )
                for entry in data.get("feedback_history", [])
            ],
            last_continued_at=datetime.fromisoformat(data["last_continued_at"]) if data.get("last_continued_at") else None,
            continuation_count=data.get("continuation_count", 0)
        )

    def create_task(self, description: str, branch_name: str) -> TaskMetadata:
        """Create a new task with metadata.

        Args:
            description: The task description
            branch_name: Git branch name for the task

        Returns:
            Created TaskMetadata instance
        """
        task_id = str(uuid.uuid4())
        task = TaskMetadata(
            id=task_id,
            description=description,
            status=TaskStatus.CREATED,
            branch_name=branch_name,
            created_at=datetime.now()
        )

        # Create task directory structure
        task_dir = self._get_task_dir(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "feedback").mkdir(exist_ok=True)
        (task_dir / "logs").mkdir(exist_ok=True)

        # Save task metadata
        metadata_file = task_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(self._serialize_task(task), f, indent=2)

        # Save initial description as first feedback entry
        with open(task_dir / "feedback" / "001_initial.md", 'w') as f:
            f.write(description)

        # Update registry
        registry = self._load_registry()
        registry[task_id] = {
            "branch_name": branch_name,
            "created_at": task.created_at.isoformat(),
            "status": task.status.value,
            "pr_url": None
        }
        self._save_registry(registry)

        return task

    def get_task(self, task_id: str) -> Optional[TaskMetadata]:
        """Get task metadata by ID.

        Args:
            task_id: The task ID

        Returns:
            TaskMetadata if found, None otherwise
        """
        task_dir = self._get_task_dir(task_id)
        metadata_file = task_dir / "metadata.json"

        if not metadata_file.exists():
            return None

        with open(metadata_file) as f:
            data = json.load(f)

        return self._deserialize_task(data)

    def update_task(self, task_id: str, **updates) -> None:
        """Update task metadata.

        Args:
            task_id: The task ID
            **updates: Fields to update
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Update fields
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)

        # Save updated metadata
        task_dir = self._get_task_dir(task_id)
        metadata_file = task_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(self._serialize_task(task), f, indent=2)

        # Update registry if needed
        registry = self._load_registry()
        if task_id in registry:
            if "status" in updates:
                registry[task_id]["status"] = updates["status"].value if hasattr(updates["status"], "value") else updates["status"]
            if "pr_url" in updates:
                registry[task_id]["pr_url"] = updates["pr_url"]
            self._save_registry(registry)

    def add_feedback(self, task_id: str, feedback: str, feedback_type: str = "text") -> None:
        """Add feedback to a task.

        Args:
            task_id: The task ID
            feedback: The feedback content
            feedback_type: Type of feedback (text, file, inline)
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Create feedback entry
        entry = FeedbackEntry(
            timestamp=datetime.now(),
            feedback=feedback,
            feedback_type=feedback_type
        )

        # Add to task history
        task.feedback_history.append(entry)
        task.continuation_count += 1
        task.last_continued_at = datetime.now()
        task.status = TaskStatus.CONTINUED

        # Save feedback to file
        task_dir = self._get_task_dir(task_id)
        feedback_num = task.continuation_count + 1
        feedback_file = task_dir / "feedback" / f"{feedback_num:03d}_continue.md"
        with open(feedback_file, 'w') as f:
            f.write(feedback)

        # Update task metadata
        self.update_task(task_id,
                         feedback_history=task.feedback_history,
                         continuation_count=task.continuation_count,
                         last_continued_at=task.last_continued_at,
                         status=task.status)

    def get_feedback_history(self, task_id: str) -> list[FeedbackEntry]:
        """Get feedback history for a task.

        Args:
            task_id: The task ID

        Returns:
            List of feedback entries
        """
        task = self.get_task(task_id)
        if not task:
            return []
        return task.feedback_history

    def list_tasks(self, status: Optional[TaskStatus] = None) -> list[TaskMetadata]:
        """List all tasks, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of TaskMetadata instances
        """
        registry = self._load_registry()
        tasks = []

        for task_id in registry:
            task = self.get_task(task_id)
            if task:
                if status is None or task.status == status:
                    tasks.append(task)

        # Sort by created_at, newest first
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks

    def delete_task(self, task_id: str) -> None:
        """Delete a task and all associated data.

        Args:
            task_id: The task ID
        """
        # Remove from registry
        registry = self._load_registry()
        if task_id in registry:
            del registry[task_id]
            self._save_registry(registry)

        # Remove task directory
        task_dir = self._get_task_dir(task_id)
        if task_dir.exists():
            shutil.rmtree(task_dir)

    def search_tasks(self, query: str) -> list[TaskMetadata]:
        """Search tasks by description.

        Args:
            query: Search query string

        Returns:
            List of matching TaskMetadata instances
        """
        tasks = self.list_tasks()
        query_lower = query.lower()

        matching_tasks = [
            task for task in tasks
            if query_lower in task.description.lower()
        ]

        return matching_tasks

    def lookup_task_by_pr(self, pr_url: str) -> Optional[TaskMetadata]:
        """Look up a task by its PR URL.

        Args:
            pr_url: GitHub PR URL

        Returns:
            TaskMetadata if found, None otherwise
        """
        registry = self._load_registry()

        for task_id, task_info in registry.items():
            if task_info.get("pr_url") == pr_url:
                return self.get_task(task_id)

        return None

    def save_task_log(self, task_id: str, log_type: str, content: str) -> None:
        """Save a log file for a task.

        Args:
            task_id: The task ID
            log_type: Type of log (e.g., 'claude_output', 'execution')
            content: Log content to save
        """
        task_dir = self._get_task_dir(task_id)
        log_file = task_dir / "logs" / f"{log_type}.log"

        with open(log_file, 'w') as f:
            f.write(content)

    def get_task_log(self, task_id: str, log_type: str) -> Optional[str]:
        """Get a log file for a task.

        Args:
            task_id: The task ID
            log_type: Type of log to retrieve

        Returns:
            Log content if found, None otherwise
        """
        task_dir = self._get_task_dir(task_id)
        log_file = task_dir / "logs" / f"{log_type}.log"

        if log_file.exists():
            with open(log_file) as f:
                return f.read()

        return None

    def get_task_history(self, limit: Optional[int] = None, branch: Optional[str] = None) -> list[TaskMetadata]:
        """Get task execution history.

        Args:
            limit: Maximum number of tasks to return
            branch: Filter by branch name

        Returns:
            List of TaskMetadata instances sorted by creation time (newest first)
        """
        tasks = self.list_tasks()

        # Filter by branch if specified
        if branch:
            tasks = [task for task in tasks if task.branch_name == branch]

        # Apply limit if specified
        if limit:
            tasks = tasks[:limit]

        return tasks
