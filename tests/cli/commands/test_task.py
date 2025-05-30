"""Tests for task command."""

import pytest
from unittest.mock import MagicMock, patch, call
from click.testing import CliRunner
from pathlib import Path
from datetime import datetime

from claude_container.cli.commands.task import task
from claude_container.models.task import TaskStatus, TaskMetadata, FeedbackEntry


class TestTaskCommand:
    """Test task command functionality."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create a CLI runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_task(self):
        """Create a mock task."""
        return TaskMetadata(
            id="test-task-id-123",
            description="Test task description",
            status=TaskStatus.CREATED,
            branch_name="test-branch",
            created_at=datetime.now(),
            continuation_count=0
        )
    
    def test_task_help(self, cli_runner):
        """Test task command help."""
        result = cli_runner.invoke(task, ['--help'])
        
        assert result.exit_code == 0
        assert "Manage Claude tasks" in result.output
        assert "create" in result.output
        assert "continue" in result.output
        assert "list" in result.output
        assert "show" in result.output
        assert "delete" in result.output
    
    # Tests for CREATE command
    @patch('claude_container.cli.commands.task.check_claude_auth')
    def test_create_no_auth(self, mock_auth, cli_runner):
        """Test task create when authentication fails."""
        mock_auth.return_value = False
        
        result = cli_runner.invoke(task, ['create'])
        
        assert result.exit_code == 1
        mock_auth.assert_called_once()
    
    @patch('claude_container.cli.commands.task.check_claude_auth')
    def test_create_no_container(self, mock_auth, cli_runner):
        """Test task create when no container exists."""
        mock_auth.return_value = True
        
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(task, ['create'])
            
            assert result.exit_code == 1
            assert "No container found" in result.output
    
    @patch('claude_container.cli.commands.task.subprocess.run')
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    @patch('claude_container.cli.commands.task.ContainerRunner')
    @patch('claude_container.cli.commands.task.check_claude_auth')
    def test_create_success(self, mock_auth, mock_runner_class, mock_storage_class, mock_subprocess, cli_runner, mock_task):
        """Test successful task create."""
        mock_auth.return_value = True
        
        # Mock storage manager
        mock_storage = MagicMock()
        mock_storage.create_task.return_value = mock_task
        mock_storage_class.return_value = mock_storage
        
        # Mock ContainerRunner
        mock_runner = MagicMock()
        mock_runner.docker_client.image_exists.return_value = True
        
        # Mock container
        mock_container = MagicMock()
        mock_container.id = "container-123"
        mock_container.exec_run.side_effect = [
            # mkdir -p /workspace/.claude
            MagicMock(exit_code=0, output=b""),
            # echo settings > settings.local.json
            MagicMock(exit_code=0, output=b""),
            # grep gitignore check
            MagicMock(exit_code=1, output=b""),  # Not found
            # echo to gitignore
            MagicMock(exit_code=0, output=b""),
            # git checkout -b branch
            MagicMock(exit_code=0, output=b"Switched to a new branch 'test-branch'"),
            # git pull
            MagicMock(exit_code=0, output=b"Already up to date"),
            # claude command - first run
            MagicMock(exit_code=0, output=[b"Task completed"]),
            # git status --porcelain
            MagicMock(exit_code=0, output=b"M src/index.js"),
            # claude command - second run for commit
            MagicMock(exit_code=0, output=[b"Committing changes"]),
            # git log -1 --pretty=%B
            MagicMock(exit_code=0, output=b"Add feature X\n\nImplemented feature X as requested"),
            # git rev-parse HEAD
            MagicMock(exit_code=0, output=b"abc123def456"),
            # git push
            MagicMock(exit_code=0, output=b"Branch pushed")
        ]
        mock_runner.create_persistent_container.return_value = mock_container
        mock_runner_class.return_value = mock_runner
        
        # Mock gh pr create
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/example/repo/pull/123"
        )
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(
                task,
                ['create', '--branch', 'test-branch'],
                input="Implement test feature\n"
            )
            
            assert result.exit_code == 0
            assert "Created task" in result.output
            assert "Starting task on branch 'test-branch'" in result.output
            assert "Task completed successfully" in result.output
            
            # Verify storage interactions
            mock_storage.create_task.assert_called_once_with("Implement test feature", "test-branch")
            assert mock_storage.update_task.call_count >= 3  # started, commit hash, completed
            
            # Verify cleanup
            mock_container.stop.assert_called_once()
            mock_container.remove.assert_called_once()
    
    # Tests for CONTINUE command
    @patch('claude_container.cli.commands.task.check_claude_auth')
    def test_continue_no_auth(self, mock_auth, cli_runner):
        """Test task continue when authentication fails."""
        mock_auth.return_value = False
        
        result = cli_runner.invoke(task, ['continue', 'task-id'])
        
        assert result.exit_code == 1
        mock_auth.assert_called_once()
    
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    @patch('claude_container.cli.commands.task.ContainerRunner')
    @patch('claude_container.cli.commands.task.check_claude_auth')
    def test_continue_success(self, mock_auth, mock_runner_class, mock_storage_class, cli_runner, mock_task):
        """Test successful task continue."""
        mock_auth.return_value = True
        
        # Mock storage manager
        mock_storage = MagicMock()
        mock_storage.get_task.return_value = mock_task
        mock_storage_class.return_value = mock_storage
        
        # Mock ContainerRunner
        mock_runner = MagicMock()
        mock_runner.docker_client.image_exists.return_value = True
        
        # Mock container
        mock_container = MagicMock()
        mock_container.id = "container-456"
        mock_container.exec_run.side_effect = [
            # mkdir -p /workspace/.claude
            MagicMock(exit_code=0, output=b""),
            # echo settings > settings.local.json
            MagicMock(exit_code=0, output=b""),
            # git checkout branch
            MagicMock(exit_code=0, output=b"Switched to branch 'test-branch'"),
            # git pull
            MagicMock(exit_code=0, output=b"Already up to date"),
            # claude command
            MagicMock(exit_code=0, output=[b"Continuing task"]),
            # git status --porcelain
            MagicMock(exit_code=0, output=b"M src/index.js"),
            # claude commit
            MagicMock(exit_code=0, output=[b"Committing changes"]),
            # git push
            MagicMock(exit_code=0, output=b"Branch pushed")
        ]
        mock_runner.create_persistent_container.return_value = mock_container
        mock_runner_class.return_value = mock_runner
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(
                task,
                ['continue', 'test-task-id-123', '--feedback', 'Fix the bug']
            )
            
            assert result.exit_code == 0
            assert "Continuing task" in result.output
            assert "Task continuation completed" in result.output
            
            # Verify feedback was added
            mock_storage.add_feedback.assert_called_once_with(
                'test-task-id-123', 'Fix the bug', 'inline'
            )
    
    # Tests for LIST command
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    @patch('claude_container.core.docker_client.DockerClient')
    def test_list_with_tasks(self, mock_docker_client_class, mock_storage_class, cli_runner, mock_task):
        """Test list command with stored tasks."""
        # Mock storage
        mock_storage = MagicMock()
        mock_storage.list_tasks.return_value = [mock_task]
        mock_storage_class.return_value = mock_storage
        
        # Mock Docker client
        mock_docker_client = MagicMock()
        mock_docker_client.list_task_containers.return_value = []
        mock_docker_client_class.return_value = mock_docker_client
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(task, ['list'])
            
            assert result.exit_code == 0
            assert "Stored tasks for project" in result.output
            assert mock_task.id[:8] in result.output
            assert mock_task.branch_name in result.output
    
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    def test_list_filter_by_status(self, mock_storage_class, cli_runner):
        """Test list command with status filter."""
        # Mock storage
        mock_storage = MagicMock()
        mock_storage.list_tasks.return_value = []
        mock_storage_class.return_value = mock_storage
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(task, ['list', '--status', 'failed'])
            
            assert result.exit_code == 0
            mock_storage.list_tasks.assert_called_once_with(TaskStatus.FAILED)
    
    # Tests for SHOW command
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    def test_show_task(self, mock_storage_class, cli_runner, mock_task):
        """Test show command."""
        # Add some data to the mock task
        mock_task.pr_url = "https://github.com/test/repo/pull/1"
        mock_task.commit_hash = "abc123"
        mock_task.feedback_history = [
            FeedbackEntry(
                timestamp=datetime.now(),
                feedback="Test feedback",
                feedback_type="text"
            )
        ]
        
        # Mock storage
        mock_storage = MagicMock()
        mock_storage.get_task.return_value = mock_task
        mock_storage_class.return_value = mock_storage
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(task, ['show', 'test-task-id', '--feedback-history'])
            
            assert result.exit_code == 0
            assert "Task Details:" in result.output
            assert mock_task.id in result.output
            assert mock_task.branch_name in result.output
            assert mock_task.pr_url in result.output
            assert "Feedback History" in result.output
    
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    def test_show_task_not_found(self, mock_storage_class, cli_runner):
        """Test show command when task not found."""
        # Mock storage
        mock_storage = MagicMock()
        mock_storage.get_task.return_value = None
        mock_storage.list_tasks.return_value = []
        mock_storage_class.return_value = mock_storage
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(task, ['show', 'non-existent'])
            
            assert result.exit_code == 1
            assert "No task found" in result.output
    
    # Tests for DELETE command
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    def test_delete_task(self, mock_storage_class, cli_runner, mock_task):
        """Test delete command."""
        # Mock storage - simulate short ID lookup
        mock_storage = MagicMock()
        mock_storage.get_task.side_effect = lambda id: mock_task if id == 'test-task-id-123' else None
        mock_storage.list_tasks.return_value = [mock_task]
        mock_storage_class.return_value = mock_storage
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(task, ['delete', 'test-task-id', '--yes'])
            
            assert result.exit_code == 0
            assert "deleted successfully" in result.output
            # Should delete with full ID after resolving
            mock_storage.delete_task.assert_called_once_with('test-task-id-123')
    
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    def test_delete_task_cancelled(self, mock_storage_class, cli_runner, mock_task):
        """Test delete command when cancelled."""
        # Mock storage
        mock_storage = MagicMock()
        mock_storage.get_task.return_value = mock_task
        mock_storage_class.return_value = mock_storage
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(task, ['delete', 'test-task-id'], input='n\n')
            
            assert result.exit_code == 1
            mock_storage.delete_task.assert_not_called()
    
    # Test edge cases
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    def test_short_id_support(self, mock_storage_class, cli_runner, mock_task):
        """Test that short IDs work for various commands."""
        # Mock storage
        mock_storage = MagicMock()
        mock_storage.get_task.return_value = None  # Not found by full ID
        mock_storage.list_tasks.return_value = [mock_task]  # Found by searching
        mock_storage_class.return_value = mock_storage
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            
            # Test show with short ID
            result = cli_runner.invoke(task, ['show', 'test-task'])
            assert result.exit_code == 0
            assert mock_task.id in result.output
    
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    @patch('claude_container.cli.commands.task.ContainerRunner')
    @patch('claude_container.cli.commands.task.check_claude_auth')
    def test_continue_by_pr_url(self, mock_auth, mock_runner_class, mock_storage_class, cli_runner, mock_task):
        """Test continuing a task by PR URL."""
        mock_auth.return_value = True
        
        # Mock storage manager
        mock_storage = MagicMock()
        mock_storage.lookup_task_by_pr.return_value = mock_task
        mock_storage_class.return_value = mock_storage
        
        # Mock ContainerRunner
        mock_runner = MagicMock()
        mock_runner.docker_client.image_exists.return_value = True
        
        # Mock container
        mock_container = MagicMock()
        mock_container.id = "container-789"
        mock_container.exec_run.return_value = MagicMock(exit_code=0, output=b"")
        mock_runner.create_persistent_container.return_value = mock_container
        mock_runner_class.return_value = mock_runner
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(
                task,
                ['continue', 'https://github.com/test/repo/pull/123', '--feedback', 'Update docs']
            )
            
            # Should look up by PR URL
            mock_storage.lookup_task_by_pr.assert_called_once_with('https://github.com/test/repo/pull/123')
    
    # Test error handling
    @patch('claude_container.cli.commands.task.subprocess.run')
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    @patch('claude_container.cli.commands.task.ContainerRunner')
    @patch('claude_container.cli.commands.task.check_claude_auth')
    def test_create_with_error_after_task_created(self, mock_auth, mock_runner_class, mock_storage_class, mock_subprocess, cli_runner, mock_task):
        """Test task create when an error occurs after task is created."""
        mock_auth.return_value = True
        
        # Mock storage manager
        mock_storage = MagicMock()
        mock_storage.create_task.return_value = mock_task
        mock_storage_class.return_value = mock_storage
        
        # Mock ContainerRunner successfully
        mock_runner = MagicMock()
        mock_runner.docker_client.image_exists.return_value = True
        
        # Mock container that will fail on exec_run
        mock_container = MagicMock()
        mock_container.id = "container-123"
        mock_container.exec_run.side_effect = Exception("Container execution failed")
        mock_runner.create_persistent_container.return_value = mock_container
        mock_runner_class.return_value = mock_runner
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(
                task,
                ['create', '--branch', 'test-branch'],
                input="Test task\n"
            )
            
            assert result.exit_code == 1
            assert "Error during task execution" in result.output
            
            # Should update task status to failed
            # Find the call that sets status to FAILED
            update_calls = [call for call in mock_storage.update_task.call_args_list 
                           if call[1].get('status') == TaskStatus.FAILED]
            
            assert len(update_calls) == 1
            failed_call = update_calls[0]
            assert failed_call[1]['status'] == TaskStatus.FAILED
            assert 'error_message' in failed_call[1]
            assert failed_call[1]['container_id'] is None
            assert 'completed_at' in failed_call[1]