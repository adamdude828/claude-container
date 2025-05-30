"""Task storage data models."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class TaskStatus(Enum):
    """Task status enumeration."""
    CREATED = "created"
    CONTINUED = "continued"
    FAILED = "failed"


@dataclass
class FeedbackEntry:
    """Represents a single feedback entry for a task."""
    timestamp: datetime
    feedback: str
    feedback_type: str  # "text", "file", "inline"
    claude_response_summary: Optional[str] = None


@dataclass
class TaskMetadata:
    """Task metadata model for persistent storage."""
    id: str  # UUID
    description: str  # User-provided task description
    status: TaskStatus  # Current status
    branch_name: str  # Git branch name
    created_at: datetime  # When task was created
    started_at: Optional[datetime] = None  # When execution began
    completed_at: Optional[datetime] = None  # When execution finished
    container_id: Optional[str] = None  # Docker container ID (if running)
    pr_url: Optional[str] = None  # GitHub PR URL (if created)
    commit_hash: Optional[str] = None  # Git commit hash (if committed)
    error_message: Optional[str] = None  # Error details (if failed)
    feedback_history: List[FeedbackEntry] = field(default_factory=list)  # All feedback provided
    last_continued_at: Optional[datetime] = None  # When task was last continued
    continuation_count: int = 0  # Number of times continued