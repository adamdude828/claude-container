import pytest
import subprocess
from unittest.mock import patch, MagicMock
from pathlib import Path
from click.testing import CliRunner
from claude_container.cli.commands.build import build


class TestBuildCommand:
    """Smoke tests for build command."""
    
    @patch('claude_container.cli.commands.build.subprocess.check_output')
    @patch('claude_container.cli.commands.build.DockerClient')
    @patch('claude_container.cli.commands.build.ConfigManager')
    @patch('claude_container.core.dockerfile_generator.DockerfileGenerator')
    @patch('claude_container.cli.commands.build.PathFinder')
    def test_build_command_success(self, mock_path_finder_class, mock_generator_class, 
                                  mock_config_manager_class, mock_docker_client_class, mock_subprocess, cli_runner):
        """Test successful build command."""
        # Setup git config mocks
        mock_subprocess.side_effect = ["test@example.com", "Test User"]
        
        # Setup mocks
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = False
        mock_docker_client_class.return_value = mock_docker
        
        mock_path_finder = MagicMock()
        mock_path_finder.find_claude_code.return_value = "/usr/local/bin/claude"
        mock_path_finder_class.return_value = mock_path_finder
        
        mock_config_manager = MagicMock()
        mock_config = MagicMock()
        mock_config_manager.get_container_config.return_value = mock_config
        mock_config_manager_class.return_value = mock_config_manager
        
        mock_generator = MagicMock()
        mock_generator.generate_cached.return_value = "FROM python:3.10\nCOPY . /app"
        mock_generator_class.return_value = mock_generator
        
        # Run command
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(build, [])
        
        # Verify
        assert result.exit_code == 0
        assert "Building container for project" in result.output
        assert "Container image built" in result.output
        mock_docker.build_image.assert_called_once()
    
    @patch('claude_container.cli.commands.build.DockerClient')
    def test_build_command_docker_not_running(self, mock_docker_client_class, cli_runner):
        """Test build command when Docker is not running."""
        mock_docker_client_class.side_effect = RuntimeError("Docker daemon is not running")
        
        result = cli_runner.invoke(build, [])
        
        assert result.exit_code == 0  # Click doesn't propagate exit code from return
        assert "Error: Docker daemon is not running" in result.output
    
    @patch('claude_container.cli.commands.build.DockerClient')
    @patch('claude_container.cli.commands.build.PathFinder')
    def test_build_command_claude_not_found(self, mock_path_finder_class, mock_docker_client_class, cli_runner):
        """Test build command when Claude Code is not found."""
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = False  # Image doesn't exist, so it will try to build
        mock_docker_client_class.return_value = mock_docker
        
        mock_path_finder = MagicMock()
        mock_path_finder.find_claude_code.return_value = None
        mock_path_finder_class.return_value = mock_path_finder
        
        result = cli_runner.invoke(build, [])
        
        assert "Claude Code executable not found" in result.output
    
    @patch('claude_container.cli.commands.build.DockerClient')
    def test_build_command_image_exists(self, mock_docker_client_class, cli_runner):
        """Test build command when image already exists."""
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = True
        mock_docker_client_class.return_value = mock_docker
        
        result = cli_runner.invoke(build, [])
        
        assert "already exists. Use --force-rebuild" in result.output
        mock_docker.build_image.assert_not_called()
    
    @patch('claude_container.cli.commands.build.subprocess.check_output')
    @patch('claude_container.cli.commands.build.DockerClient')
    @patch('claude_container.cli.commands.build.ConfigManager')
    @patch('claude_container.core.dockerfile_generator.DockerfileGenerator')
    def test_build_command_force_rebuild(self, mock_generator_class, mock_config_manager_class,
                                       mock_docker_client_class, mock_subprocess, cli_runner):
        """Test build command with --force-rebuild flag."""
        # Setup git config mocks
        mock_subprocess.side_effect = ["test@example.com", "Test User"]
        
        # Setup mocks
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = True
        mock_docker_client_class.return_value = mock_docker
        
        mock_config_manager = MagicMock()
        mock_config = MagicMock()
        mock_config_manager.get_container_config.return_value = mock_config
        mock_config_manager_class.return_value = mock_config_manager
        
        mock_generator = MagicMock()
        mock_generator.generate_cached.return_value = "FROM python:3.10"
        mock_generator_class.return_value = mock_generator
        
        # Run command
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            result = cli_runner.invoke(build, ['--force-rebuild', '--claude-code-path=/usr/local/bin/claude'])
        
        # Verify
        assert result.exit_code == 0
        assert "Removing existing image" in result.output
        mock_docker.remove_image.assert_called_once()
        mock_docker.build_image.assert_called_once()
    
    @patch('claude_container.cli.commands.build.subprocess.check_output')
    @patch('claude_container.cli.commands.build.DockerClient')
    def test_build_command_no_git_config(self, mock_docker_client_class, mock_subprocess, cli_runner):
        """Test build command when git config is not set."""
        # Setup mocks - subprocess raises error when git config not found
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'git config')
        
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = False
        mock_docker_client_class.return_value = mock_docker
        
        result = cli_runner.invoke(build, [])
        
        assert "Error: Git user configuration not found" in result.output
        assert 'git config --global user.email' in result.output
        assert 'git config --global user.name' in result.output
        mock_docker.build_image.assert_not_called()
    
    def test_build_command_help(self, cli_runner):
        """Test build command help."""
        result = cli_runner.invoke(build, ['--help'])
        
        assert result.exit_code == 0
        assert "Build Docker container" in result.output
        assert "--force-rebuild" in result.output
        assert "--tag" in result.output