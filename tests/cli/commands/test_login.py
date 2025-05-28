"""Tests for login command."""

import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from pathlib import Path

from claude_container.cli.commands.login import login


class TestLoginCommand:
    """Test login command functionality."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create a CLI runner."""
        return CliRunner()
    
    def test_login_command_no_container(self, cli_runner):
        """Test login when no container exists."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(login)
            
            assert result.exit_code == 1
            assert "No container found" in result.output
    
    @patch('claude_container.cli.commands.login.ContainerRunner')
    def test_login_command_image_not_exists(self, mock_runner_class, cli_runner):
        """Test login when image doesn't exist."""
        # Mock ContainerRunner
        mock_runner = MagicMock()
        mock_runner.docker_client.image_exists.return_value = False
        mock_runner_class.return_value = mock_runner
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(login)
            
            assert result.exit_code == 1
            assert "Container image" in result.output
            assert "not found" in result.output
    
    @patch('claude_container.cli.commands.login.ContainerRunner')
    def test_login_command_success(self, mock_runner_class, cli_runner):
        """Test successful login."""
        # Mock ContainerRunner
        mock_runner = MagicMock()
        mock_runner.docker_client.image_exists.return_value = True
        mock_runner.run_command = MagicMock()  # Mock the run_command method
        mock_runner_class.return_value = mock_runner
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(login)
            
            assert result.exit_code == 0
            assert "Starting container for authentication" in result.output
            assert "Opening bash shell" in result.output
            assert "Run 'claude login'" in result.output
            
            # Verify run_command was called with bash
            mock_runner.run_command.assert_called_once_with(['/bin/bash'])
    
    def test_login_help(self, cli_runner):
        """Test login command help."""
        result = cli_runner.invoke(login, ['--help'])
        
        assert result.exit_code == 0
        assert "Start a container and open a bash shell" in result.output