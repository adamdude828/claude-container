"""Tests for auth_check command."""

import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from pathlib import Path

from claude_container.cli.commands.auth_check import auth_check, check_claude_auth


class TestAuthCheckCommand:
    """Test auth_check command functionality."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create a CLI runner."""
        return CliRunner()
    
    def test_auth_check_command_no_container(self, cli_runner):
        """Test auth_check when no container exists."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(auth_check)
            
            assert result.exit_code == 1
            assert "No container found" in result.output
    
    @patch('claude_container.cli.commands.auth_check.ContainerRunner')
    def test_auth_check_command_image_not_exists(self, mock_runner_class, cli_runner):
        """Test auth_check when image doesn't exist."""
        # Mock ContainerRunner
        mock_runner = MagicMock()
        mock_runner.docker_client.image_exists.return_value = False
        mock_runner_class.return_value = mock_runner
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(auth_check)
            
            assert result.exit_code == 1
            assert "Container image" in result.output
            assert "not found" in result.output
    
    @patch('claude_container.cli.commands.auth_check.ContainerRunner')
    def test_auth_check_command_authenticated(self, mock_runner_class, cli_runner):
        """Test auth_check when authenticated."""
        # Mock ContainerRunner
        mock_runner = MagicMock()
        mock_runner.docker_client.image_exists.return_value = True
        
        # Mock container execution for auth check
        mock_container = MagicMock()
        mock_container.wait.return_value = {'StatusCode': 0}
        mock_runner.docker_client.client.containers.run.return_value = mock_container
        mock_runner._get_container_config.return_value = {
            'image': 'test-image',
            'volumes': {},
            'working_dir': '/workspace',
            'environment': {},
            'command': ['claude', '--model=sonnet', '-p', 'Auth check - return immediately'],
            'remove': False,
            'labels': {"claude-container": "true", "claude-container-type": "auth-check"}
        }
        mock_runner_class.return_value = mock_runner
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(auth_check)
            
            assert result.exit_code == 0
            assert "Authentication is valid" in result.output
    
    @patch('claude_container.cli.commands.auth_check.ContainerRunner')
    def test_auth_check_command_not_authenticated(self, mock_runner_class, cli_runner):
        """Test auth_check when not authenticated."""
        # Mock ContainerRunner
        mock_runner = MagicMock()
        mock_runner.docker_client.image_exists.return_value = True
        
        # Mock container execution to simulate auth failure
        mock_container = MagicMock()
        mock_container.wait.return_value = {'StatusCode': 1}
        mock_runner.docker_client.client.containers.run.return_value = mock_container
        mock_runner._get_container_config.return_value = {
            'image': 'test-image',
            'volumes': {},
            'working_dir': '/workspace',
            'environment': {},
            'command': ['claude', '--model=sonnet', '-p', 'Auth check - return immediately'],
            'remove': False,
            'labels': {"claude-container": "true", "claude-container-type": "auth-check"}
        }
        mock_runner_class.return_value = mock_runner
        
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(auth_check)
            
            assert result.exit_code == 1
            assert "expired or is invalid" in result.output
            assert "claude-container login" in result.output
    
    def test_auth_check_help(self, cli_runner):
        """Test auth_check command help."""
        result = cli_runner.invoke(auth_check, ['--help'])
        
        assert result.exit_code == 0
        assert "Check if Claude authentication is still valid" in result.output
    
    @patch('claude_container.cli.commands.auth_check.ContainerRunner')
    @patch('claude_container.cli.commands.auth_check.get_project_context')
    def test_check_claude_auth_function_success(self, mock_get_context, mock_runner_class):
        """Test check_claude_auth function returns True when authenticated."""
        # Mock get_project_context to return existing data dir
        mock_project_root = MagicMock()
        mock_data_dir = MagicMock()
        mock_data_dir.exists.return_value = True
        mock_get_context.return_value = (mock_project_root, mock_data_dir)
        
        # Mock ContainerRunner
        mock_runner = MagicMock()
        mock_runner.docker_client.image_exists.return_value = True
        mock_container = MagicMock()
        mock_container.wait.return_value = {'StatusCode': 0}
        mock_runner.docker_client.client.containers.run.return_value = mock_container
        mock_runner._get_container_config.return_value = {'test': 'config'}
        mock_runner_class.return_value = mock_runner
        
        result = check_claude_auth(quiet=True)
        
        assert result is True
        mock_container.remove.assert_called_once()
    
    @patch('claude_container.cli.commands.auth_check.ContainerRunner')
    @patch('claude_container.cli.commands.auth_check.get_project_context')
    def test_check_claude_auth_function_failure(self, mock_get_context, mock_runner_class):
        """Test check_claude_auth function returns False when not authenticated."""
        # Mock get_project_context to return existing data dir
        mock_project_root = MagicMock()
        mock_data_dir = MagicMock()
        mock_data_dir.exists.return_value = True
        mock_get_context.return_value = (mock_project_root, mock_data_dir)
        
        # Mock ContainerRunner
        mock_runner = MagicMock()
        mock_runner.docker_client.image_exists.return_value = True
        mock_container = MagicMock()
        mock_container.wait.return_value = {'StatusCode': 1}
        mock_runner.docker_client.client.containers.run.return_value = mock_container
        mock_runner._get_container_config.return_value = {'test': 'config'}
        mock_runner_class.return_value = mock_runner
        
        result = check_claude_auth(quiet=True)
        
        assert result is False
        mock_container.remove.assert_called_once()