"""Tests for TaskStorageManager."""
import json
import pytest
from datetime import datetime
from pathlib import Path

from claude_container.core.task_storage import TaskStorageManager
from claude_container.models.task import TaskStatus, FeedbackEntry


@pytest.fixture
def temp_storage_dir(tmp_path):
    """Create a temporary storage directory."""
    return tmp_path / ".claude-container"


@pytest.fixture
def storage_manager(temp_storage_dir):
    """Create a TaskStorageManager instance."""
    return TaskStorageManager(temp_storage_dir)


class TestTaskStorageManager:
    """Test cases for TaskStorageManager."""
    
    def test_init_creates_structure(self, temp_storage_dir):
        """Test that initialization creates the required directory structure."""
        manager = TaskStorageManager(temp_storage_dir)
        
        assert (temp_storage_dir / "tasks").exists()
        assert (temp_storage_dir / "tasks" / "tasks").exists()
        assert (temp_storage_dir / "tasks" / "task_registry.json").exists()
        
        # Check registry is empty
        with open(temp_storage_dir / "tasks" / "task_registry.json", 'r') as f:
            registry = json.load(f)
            assert registry == {}
    
    def test_create_task(self, storage_manager):
        """Test creating a new task."""
        description = "Test task description"
        branch = "test-branch"
        
        task = storage_manager.create_task(description, branch)
        
        # Check task attributes
        assert task.description == description
        assert task.branch_name == branch
        assert task.status == TaskStatus.CREATED
        assert task.created_at is not None
        assert task.continuation_count == 0
        assert len(task.feedback_history) == 0
        
        # Check task directory structure
        task_dir = storage_manager._get_task_dir(task.id)
        assert task_dir.exists()
        assert (task_dir / "metadata.json").exists()
        assert (task_dir / "feedback").exists()
        assert (task_dir / "logs").exists()
        assert (task_dir / "feedback" / "001_initial.md").exists()
        
        # Check initial description file
        with open(task_dir / "feedback" / "001_initial.md", 'r') as f:
            assert f.read() == description
    
    def test_get_task(self, storage_manager):
        """Test retrieving a task."""
        task = storage_manager.create_task("Test task", "test-branch")
        
        retrieved = storage_manager.get_task(task.id)
        assert retrieved is not None
        assert retrieved.id == task.id
        assert retrieved.description == task.description
        assert retrieved.branch_name == task.branch_name
        
        # Test non-existent task
        assert storage_manager.get_task("non-existent-id") is None
    
    def test_update_task(self, storage_manager):
        """Test updating task metadata."""
        task = storage_manager.create_task("Test task", "test-branch")
        
        # Update various fields
        pr_url = "https://github.com/user/repo/pull/123"
        commit_hash = "abc123def456"
        storage_manager.update_task(
            task.id,
            status=TaskStatus.CONTINUED,
            pr_url=pr_url,
            commit_hash=commit_hash,
            started_at=datetime.now()
        )
        
        # Retrieve and verify
        updated = storage_manager.get_task(task.id)
        assert updated.status == TaskStatus.CONTINUED
        assert updated.pr_url == pr_url
        assert updated.commit_hash == commit_hash
        assert updated.started_at is not None
    
    def test_add_feedback(self, storage_manager):
        """Test adding feedback to a task."""
        task = storage_manager.create_task("Test task", "test-branch")
        
        feedback1 = "First feedback"
        storage_manager.add_feedback(task.id, feedback1, "text")
        
        # Check task was updated
        updated = storage_manager.get_task(task.id)
        assert updated.continuation_count == 1
        assert updated.status == TaskStatus.CONTINUED
        assert updated.last_continued_at is not None
        assert len(updated.feedback_history) == 1
        assert updated.feedback_history[0].feedback == feedback1
        assert updated.feedback_history[0].feedback_type == "text"
        
        # Check feedback file was created
        task_dir = storage_manager._get_task_dir(task.id)
        assert (task_dir / "feedback" / "002_continue.md").exists()
        
        # Add another feedback
        feedback2 = "Second feedback"
        storage_manager.add_feedback(task.id, feedback2, "inline")
        
        updated = storage_manager.get_task(task.id)
        assert updated.continuation_count == 2
        assert len(updated.feedback_history) == 2
        assert (task_dir / "feedback" / "003_continue.md").exists()
    
    def test_list_tasks(self, storage_manager):
        """Test listing tasks."""
        # Create multiple tasks
        task1 = storage_manager.create_task("Task 1", "branch-1")
        task2 = storage_manager.create_task("Task 2", "branch-2")
        task3 = storage_manager.create_task("Task 3", "branch-3")
        
        # Update one to failed status
        storage_manager.update_task(task2.id, status=TaskStatus.FAILED)
        
        # List all tasks
        all_tasks = storage_manager.list_tasks()
        assert len(all_tasks) == 3
        
        # List by status
        created_tasks = storage_manager.list_tasks(TaskStatus.CREATED)
        assert len(created_tasks) == 2
        
        failed_tasks = storage_manager.list_tasks(TaskStatus.FAILED)
        assert len(failed_tasks) == 1
        assert failed_tasks[0].id == task2.id
    
    def test_delete_task(self, storage_manager):
        """Test deleting a task."""
        task = storage_manager.create_task("Test task", "test-branch")
        task_id = task.id
        task_dir = storage_manager._get_task_dir(task_id)
        
        # Verify task exists
        assert task_dir.exists()
        assert storage_manager.get_task(task_id) is not None
        
        # Delete task
        storage_manager.delete_task(task_id)
        
        # Verify task is gone
        assert not task_dir.exists()
        assert storage_manager.get_task(task_id) is None
        
        # Verify registry updated
        with open(storage_manager.registry_file, 'r') as f:
            registry = json.load(f)
            assert task_id not in registry
    
    def test_search_tasks(self, storage_manager):
        """Test searching tasks by description."""
        storage_manager.create_task("Implement authentication", "auth-branch")
        storage_manager.create_task("Fix authentication bug", "bugfix-branch")
        storage_manager.create_task("Add user profile", "profile-branch")
        
        # Search for "authentication"
        results = storage_manager.search_tasks("authentication")
        assert len(results) == 2
        
        # Search for "user"
        results = storage_manager.search_tasks("user")
        assert len(results) == 1
        assert "profile" in results[0].description
        
        # Case insensitive search
        results = storage_manager.search_tasks("AUTHENTICATION")
        assert len(results) == 2
    
    def test_lookup_task_by_pr(self, storage_manager):
        """Test looking up task by PR URL."""
        task1 = storage_manager.create_task("Task 1", "branch-1")
        task2 = storage_manager.create_task("Task 2", "branch-2")
        
        pr_url = "https://github.com/user/repo/pull/123"
        storage_manager.update_task(task1.id, pr_url=pr_url)
        
        # Look up by PR URL
        found = storage_manager.lookup_task_by_pr(pr_url)
        assert found is not None
        assert found.id == task1.id
        
        # Non-existent PR
        assert storage_manager.lookup_task_by_pr("https://github.com/user/repo/pull/999") is None
    
    def test_save_and_get_task_log(self, storage_manager):
        """Test saving and retrieving task logs."""
        task = storage_manager.create_task("Test task", "test-branch")
        
        log_content = "This is a test log\nWith multiple lines"
        storage_manager.save_task_log(task.id, "claude_output", log_content)
        
        # Retrieve log
        retrieved = storage_manager.get_task_log(task.id, "claude_output")
        assert retrieved == log_content
        
        # Non-existent log
        assert storage_manager.get_task_log(task.id, "non_existent") is None
    
    def test_task_serialization(self, storage_manager):
        """Test task serialization and deserialization."""
        task = storage_manager.create_task("Test task", "test-branch")
        
        # Add some data
        storage_manager.add_feedback(task.id, "Test feedback", "text")
        storage_manager.update_task(
            task.id,
            pr_url="https://github.com/test/repo/pull/1",
            commit_hash="abc123",
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
        
        # Get fresh copy
        retrieved = storage_manager.get_task(task.id)
        
        # Verify all fields preserved
        assert retrieved.description == task.description
        assert retrieved.branch_name == task.branch_name
        assert retrieved.continuation_count == 1
        assert len(retrieved.feedback_history) == 1
        assert retrieved.pr_url == "https://github.com/test/repo/pull/1"
        assert retrieved.commit_hash == "abc123"
        assert retrieved.started_at is not None
        assert retrieved.completed_at is not None