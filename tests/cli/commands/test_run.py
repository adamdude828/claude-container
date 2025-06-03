import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from click.testing import CliRunner
from claude_container.cli.commands.run import run


class TestRunCommand:
    """Smoke tests for run command."""
    
    @patch('claude_container.cli.commands.run.ContainerRunner')
    @patch('claude_container.cli.commands.run.DockerClient')
    def test_run_command_success(self, mock_docker_client_class, mock_runner_class, cli_runner):
        """Test successful run command."""
        # Setup mocks
        mock_docker = MagicMock()
        mock_docker_client_class.return_value = mock_docker
        
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner
        
        # Run command in isolated filesystem
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(run, ['echo', 'hello'])
        
        # Verify
        assert result.exit_code == 0
        assert "Running in container with Claude Code" in result.output
        mock_runner.run_command.assert_called_once_with(['echo', 'hello'], user='node')
    
    def test_run_command_no_container(self, cli_runner):
        """Test run command when no container exists."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(run, ['echo', 'hello'])
        
        assert result.exit_code == 0  # Click returns 0 even on early return
        assert "No container found. Please run 'build' first." in result.output
    
    @patch('claude_container.cli.commands.run.DockerClient')
    def test_run_command_docker_not_running(self, mock_docker_client_class, cli_runner):
        """Test run command when Docker is not running."""
        mock_docker_client_class.side_effect = RuntimeError("Docker daemon is not running")
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(run, ['echo', 'hello'])
        
        assert "Error: Docker daemon is not running" in result.output
    
    @patch('claude_container.cli.commands.run.ContainerRunner')
    @patch('claude_container.cli.commands.run.DockerClient')
    def test_run_command_with_complex_args(self, mock_docker_client_class, mock_runner_class, cli_runner):
        """Test run command with complex arguments."""
        # Setup mocks
        mock_docker = MagicMock()
        mock_docker_client_class.return_value = mock_docker
        
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner
        
        # Run command
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(run, ['python', '-c', 'print("Hello, World!")'])
        
        # Verify
        assert result.exit_code == 0
        mock_runner.run_command.assert_called_once_with(['python', '-c', 'print("Hello, World!")'], user='node')
    
    @patch('claude_container.cli.commands.run.ContainerRunner')
    @patch('claude_container.cli.commands.run.DockerClient')
    def test_run_command_no_args(self, mock_docker_client_class, mock_runner_class, cli_runner):
        """Test run command with no arguments."""
        # Setup mocks
        mock_docker = MagicMock()
        mock_docker_client_class.return_value = mock_docker
        
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner
        
        # Run command
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(run, [])
        
        # Verify - should call run_command with empty list
        assert result.exit_code == 0
        mock_runner.run_command.assert_called_once_with([], user='node')
    
    def test_run_command_help(self, cli_runner):
        """Test run command help."""
        result = cli_runner.invoke(run, ['--help'])
        
        assert result.exit_code == 0
        assert "Run command in the container" in result.output