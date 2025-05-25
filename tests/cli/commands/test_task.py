"""Tests for the task command."""
import json
from unittest.mock import patch, MagicMock
import pytest
from click.testing import CliRunner

from claude_container.cli.commands.task import task


class TestTaskCommand:
    """Test suite for task commands."""
    
    def test_task_help(self, cli_runner):
        """Test task help command."""
        result = cli_runner.invoke(task, ['--help'])
        assert result.exit_code == 0
        assert 'Manage Claude tasks' in result.output

    @patch('claude_container.cli.commands.task.DaemonClient')
    @patch('claude_container.cli.commands.task.subprocess.run')
    @patch('claude_container.cli.commands.task.click.prompt')
    def test_task_start_success(self, mock_prompt, mock_subprocess, mock_daemon_client, cli_runner):
        """Test successful task creation."""
        # Setup mocks
        mock_prompt.side_effect = ['feature-branch', 'Add new feature']
        
        # Mock git operations
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout='clean working directory',
            stderr=''
        )
        
        # Mock daemon client
        mock_client = MagicMock()
        mock_client.submit_task.return_value = {
            'task_id': 'task-123',
            'status': 'submitted'
        }
        mock_daemon_client.return_value = mock_client
        
        result = cli_runner.invoke(task, ['start'])
        
        assert result.exit_code == 0
        assert 'Task started successfully!' in result.output
        assert 'Task ID: task-123' in result.output
        
        # Verify submit_task was called with metadata
        mock_client.submit_task.assert_called_once()
        call_args = mock_client.submit_task.call_args[1]
        assert call_args['metadata']['branch'] == 'feature-branch'
        assert call_args['metadata']['task_description'] == 'Add new feature'
        assert call_args['metadata']['type'] == 'feature_task'

    @patch('claude_container.cli.commands.task.click.prompt')
    def test_task_start_empty_branch(self, mock_prompt, cli_runner):
        """Test task start with empty branch name."""
        mock_prompt.side_effect = ['', 'Add new feature']
        
        result = cli_runner.invoke(task, ['start'])
        
        assert result.exit_code == 0
        assert 'Branch name cannot be empty' in result.output

    @patch('claude_container.cli.commands.task.DaemonClient')
    def test_task_list_success(self, mock_daemon_client, cli_runner):
        """Test successful task listing."""
        mock_client = MagicMock()
        mock_client.list_tasks.return_value = {
            'tasks': [
                {
                    'id': 'task-123',
                    'state': 'running',
                    'command': ['claude-code', '-p', 'test'],
                    'branch_name': 'feature-1',
                    'pr_url': 'https://github.com/user/repo/pull/1'
                },
                {
                    'id': 'task-456',
                    'state': 'completed',
                    'command': ['claude-code', '-p', 'test2'],
                    'branch_name': 'feature-2',
                    'pr_url': None
                }
            ]
        }
        mock_daemon_client.return_value = mock_client
        
        result = cli_runner.invoke(task, ['list'])
        
        assert result.exit_code == 0
        assert 'task-123' in result.output
        assert 'running' in result.output
        assert 'task-456' in result.output
        assert 'completed' in result.output
        assert 'Found 2 task(s):' in result.output

    @patch('claude_container.cli.commands.task.DaemonClient')
    def test_task_list_empty(self, mock_daemon_client, cli_runner):
        """Test task list when no tasks exist."""
        mock_client = MagicMock()
        mock_client.list_tasks.return_value = {'tasks': []}
        mock_daemon_client.return_value = mock_client
        
        result = cli_runner.invoke(task, ['list'])
        
        assert result.exit_code == 0
        assert 'No tasks found' in result.output

    @patch('claude_container.cli.commands.task.DaemonClient')
    def test_task_status_success(self, mock_daemon_client, cli_runner):
        """Test successful task status retrieval."""
        mock_client = MagicMock()
        mock_client.get_status.return_value = {
            'state': 'running',
            'command': ['claude-code', '-p', 'test'],
            'working_dir': '/test/dir',
            'started_at': '2024-01-01T10:00:00'
        }
        mock_daemon_client.return_value = mock_client
        
        result = cli_runner.invoke(task, ['status', 'task-123'])
        
        assert result.exit_code == 0
        assert 'Task task-123:' in result.output
        assert 'State: running' in result.output
        assert 'Command: claude-code -p test' in result.output
        assert 'Working Directory: /test/dir' in result.output

    @patch('claude_container.cli.commands.task.DaemonClient')
    def test_task_output_success(self, mock_daemon_client, cli_runner):
        """Test successful task output retrieval."""
        mock_client = MagicMock()
        mock_client.get_output.return_value = {
            'task_id': 'task-123',
            'output': 'Task completed successfully\nAll tests passed'
        }
        mock_daemon_client.return_value = mock_client
        
        result = cli_runner.invoke(task, ['output', 'task-123'])
        
        assert result.exit_code == 0
        assert 'Task completed successfully' in result.output
        assert 'All tests passed' in result.output

    @patch('claude_container.cli.commands.task.DaemonClient')
    def test_task_daemon_connection_error(self, mock_daemon_client, cli_runner):
        """Test handling of daemon connection errors."""
        mock_daemon_client.side_effect = ConnectionError("Daemon not running")
        
        result = cli_runner.invoke(task, ['list'])
        
        assert result.exit_code != 0
        assert result.exception is not None

    @patch('claude_container.cli.commands.task.DaemonClient')
    @patch('claude_container.cli.commands.task.subprocess.run')
    @patch('claude_container.cli.commands.task.click.prompt')
    def test_task_start_daemon_not_running(self, mock_prompt, mock_subprocess, mock_daemon_client, cli_runner):
        """Test task start fails immediately when daemon is not running."""
        mock_prompt.side_effect = ['feature-branch', 'Add new feature']
        
        # Mock successful git operations
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout='main',
            stderr=''
        )
        
        # Mock daemon connection failure on initialization
        mock_daemon_client.side_effect = ConnectionError("Cannot connect to daemon")
        
        result = cli_runner.invoke(task, ['start'])
        
        assert result.exit_code != 0
        assert 'Cannot connect to daemon' in result.output or 'is it running?' in result.output
        
        # Verify we didn't create or push the branch since daemon wasn't running
        # Should have NO subprocess calls since we failed early
        assert mock_subprocess.call_count == 0
        # Also verify prompts weren't called
        assert mock_prompt.call_count == 0

    def test_task_help_commands(self, cli_runner):
        """Test help for various task subcommands."""
        # Test task start help
        result = cli_runner.invoke(task, ['start', '--help'])
        assert result.exit_code == 0
        assert 'Start a new task' in result.output
        
        # Test task list help
        result = cli_runner.invoke(task, ['list', '--help'])
        assert result.exit_code == 0
        assert 'List all tasks' in result.output
        
        # Test task status help
        result = cli_runner.invoke(task, ['status', '--help'])
        assert result.exit_code == 0
        assert 'Get status' in result.output