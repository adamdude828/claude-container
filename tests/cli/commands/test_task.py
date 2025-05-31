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
    
    # Tests for LOGS command
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    def test_logs_command(self, mock_storage_class, cli_runner, mock_task, tmp_path):
        """Test task logs command."""
        # Create task directory structure with logs
        task_dir = tmp_path / ".claude-container" / "tasks" / "tasks" / mock_task.id
        logs_dir = task_dir / "logs"
        logs_dir.mkdir(parents=True)
        
        # Create a log file
        log_content = "This is test log output\nLine 2 of log\nLine 3 of log"
        log_file = logs_dir / "claude_output.log"
        log_file.write_text(log_content)
        
        # Mock storage manager
        mock_storage = MagicMock()
        mock_storage.get_task.return_value = mock_task
        mock_storage_class.return_value = mock_storage
        
        with cli_runner.isolated_filesystem():
            # Create necessary structure
            Path(".claude-container").mkdir()
            
            # Copy the log structure to current dir
            import shutil
            shutil.copytree(tmp_path / ".claude-container", ".claude-container", dirs_exist_ok=True)
            
            result = cli_runner.invoke(task, ['logs', mock_task.id])
            
            assert result.exit_code == 0
            assert "Execution Logs for Task" in result.output
            assert log_content in result.output
    
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    def test_logs_command_with_feedback(self, mock_storage_class, cli_runner, mock_task):
        """Test task logs command with --feedback flag."""
        # Add feedback history to mock task
        mock_task.feedback_history = [
            FeedbackEntry(
                timestamp=datetime.now(),
                feedback="Please add error handling",
                feedback_type="text"
            ),
            FeedbackEntry(
                timestamp=datetime.now(),
                feedback="Add type hints",
                feedback_type="inline",
                claude_response_summary="Added type hints to all functions"
            )
        ]
        
        # Mock storage manager
        mock_storage = MagicMock()
        mock_storage.get_task.return_value = mock_task
        mock_storage_class.return_value = mock_storage
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            
            result = cli_runner.invoke(task, ['logs', mock_task.id, '--feedback'])
            
            assert result.exit_code == 0
            assert "Feedback History for Task" in result.output
            assert "Please add error handling" in result.output
            assert "Add type hints" in result.output
            assert "Claude's Response: Added type hints to all functions" in result.output
    
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    def test_logs_command_no_logs(self, mock_storage_class, cli_runner, mock_task):
        """Test task logs command when no logs exist."""
        # Mock storage manager
        mock_storage = MagicMock()
        mock_storage.get_task.return_value = mock_task
        mock_storage_class.return_value = mock_storage
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            
            result = cli_runner.invoke(task, ['logs', mock_task.id])
            
            assert result.exit_code == 0
            assert f"No logs found for task {mock_task.id[:8]}" in result.output
    
    # Tests for SEARCH command
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    def test_search_command_with_results(self, mock_storage_class, cli_runner, mock_task):
        """Test task search command with matching results."""
        # Mock storage manager
        mock_storage = MagicMock()
        mock_storage.search_tasks.return_value = [mock_task]
        mock_storage_class.return_value = mock_storage
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            
            result = cli_runner.invoke(task, ['search', 'test'])
            
            assert result.exit_code == 0
            assert "Tasks matching 'test'" in result.output
            assert mock_task.id[:8] in result.output
            assert "Found 1 matching task(s)" in result.output
            
            # Verify search was called with correct query
            mock_storage.search_tasks.assert_called_once_with('test')
    
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    def test_search_command_no_results(self, mock_storage_class, cli_runner):
        """Test task search command with no matching results."""
        # Mock storage manager
        mock_storage = MagicMock()
        mock_storage.search_tasks.return_value = []
        mock_storage_class.return_value = mock_storage
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            
            result = cli_runner.invoke(task, ['search', 'nonexistent'])
            
            assert result.exit_code == 0
            assert "No tasks found matching 'nonexistent'" in result.output
    
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    def test_search_command_multiple_results(self, mock_storage_class, cli_runner):
        """Test task search command with multiple matching results."""
        # Create multiple mock tasks
        task1 = TaskMetadata(
            id="task-1",
            description="Implement authentication system",
            status=TaskStatus.CREATED,
            branch_name="auth-feature",
            created_at=datetime.now()
        )
        task2 = TaskMetadata(
            id="task-2",
            description="Fix authentication bug",
            status=TaskStatus.CONTINUED,
            branch_name="auth-bugfix",
            created_at=datetime.now()
        )
        
        # Mock storage manager
        mock_storage = MagicMock()
        mock_storage.search_tasks.return_value = [task1, task2]
        mock_storage_class.return_value = mock_storage
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            
            result = cli_runner.invoke(task, ['search', 'authentication'])
            
            assert result.exit_code == 0
            assert "Tasks matching 'authentication'" in result.output
            assert task1.id[:8] in result.output
            assert task2.id[:8] in result.output
            assert "Found 2 matching task(s)" in result.output
    
    # Tests for HISTORY command
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    def test_history_command_default(self, mock_storage_class, cli_runner, mock_task):
        """Test task history command with default options."""
        # Mock storage manager
        mock_storage = MagicMock()
        mock_storage.get_task_history.return_value = [mock_task]
        mock_storage_class.return_value = mock_storage
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            
            result = cli_runner.invoke(task, ['history'])
            
            assert result.exit_code == 0
            assert "Task history (showing up to 10 tasks)" in result.output
            assert mock_task.id[:8] in result.output
            assert "Showing 1 task(s)" in result.output
            
            # Verify history was called with default limit
            mock_storage.get_task_history.assert_called_once_with(limit=10, branch=None)
    
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    def test_history_command_with_limit(self, mock_storage_class, cli_runner):
        """Test task history command with custom limit."""
        # Mock storage manager
        mock_storage = MagicMock()
        mock_storage.get_task_history.return_value = []
        mock_storage_class.return_value = mock_storage
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            
            result = cli_runner.invoke(task, ['history', '--limit', '5'])
            
            assert result.exit_code == 0
            
            # Verify history was called with custom limit
            mock_storage.get_task_history.assert_called_once_with(limit=5, branch=None)
    
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    def test_history_command_with_branch(self, mock_storage_class, cli_runner, mock_task):
        """Test task history command filtered by branch."""
        # Mock storage manager
        mock_storage = MagicMock()
        mock_storage.get_task_history.return_value = [mock_task]
        mock_storage_class.return_value = mock_storage
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            
            result = cli_runner.invoke(task, ['history', '--branch', 'feature-x'])
            
            assert result.exit_code == 0
            assert "Task history for branch 'feature-x'" in result.output
            
            # Verify history was called with branch filter
            mock_storage.get_task_history.assert_called_once_with(limit=10, branch='feature-x')
    
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    def test_history_command_no_results(self, mock_storage_class, cli_runner):
        """Test task history command with no results."""
        # Mock storage manager
        mock_storage = MagicMock()
        mock_storage.get_task_history.return_value = []
        mock_storage_class.return_value = mock_storage
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            
            result = cli_runner.invoke(task, ['history'])
            
            assert result.exit_code == 0
            assert "No task history found" in result.output
    
    @patch('claude_container.cli.commands.task.TaskStorageManager')
    def test_history_command_with_status_breakdown(self, mock_storage_class, cli_runner):
        """Test task history command shows status breakdown when multiple statuses."""
        # Create tasks with different statuses
        tasks = [
            TaskMetadata(
                id=f"task-{i}",
                description=f"Task {i}",
                status=status,
                branch_name=f"branch-{i}",
                created_at=datetime.now()
            )
            for i, status in enumerate([TaskStatus.CREATED, TaskStatus.CONTINUED, TaskStatus.FAILED, TaskStatus.CREATED])
        ]
        
        # Mock storage manager
        mock_storage = MagicMock()
        mock_storage.get_task_history.return_value = tasks
        mock_storage_class.return_value = mock_storage
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            
            result = cli_runner.invoke(task, ['history'])
            
            assert result.exit_code == 0
            assert "Status breakdown:" in result.output
            assert "Created: 2" in result.output
            assert "Continued: 1" in result.output
            assert "Failed: 1" in result.output