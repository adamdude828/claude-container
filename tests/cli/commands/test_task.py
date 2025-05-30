"""Tests for task command."""

import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from pathlib import Path

from claude_container.cli.commands.task import task, start


class TestTaskCommand:
    """Test task command functionality."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create a CLI runner."""
        return CliRunner()
    
    @patch('claude_container.cli.commands.task.check_claude_auth')
    def test_task_start_no_auth(self, mock_auth, cli_runner):
        """Test task start when authentication fails."""
        mock_auth.return_value = False
        
        result = cli_runner.invoke(start)
        
        assert result.exit_code == 1
        mock_auth.assert_called_once()
    
    @patch('claude_container.cli.commands.task.check_claude_auth')
    def test_task_start_no_container(self, mock_auth, cli_runner):
        """Test task start when no container exists."""
        mock_auth.return_value = True
        
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(start)
            
            assert result.exit_code == 1
            assert "No container found" in result.output
    
    @patch('claude_container.cli.commands.task.ContainerRunner')
    @patch('claude_container.cli.commands.task.check_claude_auth')
    def test_task_start_image_not_exists(self, mock_auth, mock_runner_class, cli_runner):
        """Test task start when image doesn't exist."""
        mock_auth.return_value = True
        
        # Mock ContainerRunner
        mock_runner = MagicMock()
        mock_runner.docker_client.image_exists.return_value = False
        mock_runner_class.return_value = mock_runner
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(start)
            
            assert result.exit_code == 1
            assert "Container image" in result.output
            assert "not found" in result.output
    
    @patch('claude_container.cli.commands.task.subprocess.run')
    @patch('claude_container.cli.commands.task.ContainerRunner')
    @patch('claude_container.cli.commands.task.check_claude_auth')
    def test_task_start_success(self, mock_auth, mock_runner_class, mock_subprocess, cli_runner):
        """Test successful task start."""
        mock_auth.return_value = True
        
        # Mock ContainerRunner
        mock_runner = MagicMock()
        mock_runner.docker_client.image_exists.return_value = True
        
        # Mock container
        mock_container = MagicMock()
        mock_container.exec_run.side_effect = [
            # mkdir -p /workspace/.claude
            MagicMock(exit_code=0, output=b""),
            # echo settings > settings.local.json
            MagicMock(exit_code=0, output=b""),
            # grep gitignore check
            MagicMock(exit_code=1, output=b""),  # Not found
            # echo to gitignore
            MagicMock(exit_code=0, output=b""),
            # git checkout
            MagicMock(exit_code=0, output=b"Switched to branch"),
            # git pull
            MagicMock(exit_code=0, output=b"Already up to date"),
            # claude command
            MagicMock(exit_code=0, output=[b"Task completed"]),
            # git add
            MagicMock(exit_code=0, output=b""),
            # git commit
            MagicMock(exit_code=0, output=b"1 file changed"),
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
                start,
                input="test-branch\nImplement test feature\n"
            )
            
            assert result.exit_code == 0
            assert "Starting task on branch 'test-branch'" in result.output
            assert "Task completed successfully" in result.output
            
            # Verify container was created with proper method
            mock_runner.create_persistent_container.assert_called_once_with("task")
            
            # Verify cleanup
            mock_container.stop.assert_called_once()
            mock_container.remove.assert_called_once()
    
    @patch('claude_container.cli.commands.task.ContainerRunner')
    @patch('claude_container.cli.commands.task.check_claude_auth')
    def test_task_start_empty_inputs(self, mock_auth, mock_runner_class, cli_runner):
        """Test task start with empty branch name or description."""
        mock_auth.return_value = True
        
        # Mock ContainerRunner
        mock_runner = MagicMock()
        mock_runner.docker_client.image_exists.return_value = True
        mock_runner_class.return_value = mock_runner
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            
            # Test empty branch name
            result = cli_runner.invoke(start, input="  \nTest description\n")
            assert result.exit_code == 1
            assert "Branch name cannot be empty" in result.output
            
            # Test empty description
            result = cli_runner.invoke(start, input="test-branch\n  \n")
            assert result.exit_code == 1
            assert "Task description cannot be empty" in result.output
    
    def test_task_help(self, cli_runner):
        """Test task command help."""
        result = cli_runner.invoke(task, ['--help'])
        
        assert result.exit_code == 0
        assert "Manage Claude tasks" in result.output
        assert "start" in result.output