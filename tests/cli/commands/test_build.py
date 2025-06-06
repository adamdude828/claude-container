import pytest
import subprocess
from unittest.mock import patch, MagicMock
from pathlib import Path
from click.testing import CliRunner
from claude_container.cli.commands.build import build


class TestBuildCommand:
    """Smoke tests for build command."""
    
    @patch('claude_container.cli.commands.build.subprocess.check_output')
    @patch('claude_container.cli.commands.build.get_docker_client')
    @patch('claude_container.cli.commands.build.ConfigManager')
    @patch('claude_container.core.dockerfile_generator.DockerfileGenerator')
    def test_build_command_success(self, mock_generator_class, 
                                  mock_config_manager_class, mock_get_docker_client, mock_subprocess, cli_runner):
        """Test successful build command."""
        # Setup git config mocks
        mock_subprocess.side_effect = ["test@example.com", "Test User"]
        
        # Setup mocks
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = False
        mock_get_docker_client.return_value = mock_docker
        
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
    
    @patch('claude_container.cli.commands.build.get_docker_client')
    def test_build_command_docker_not_running(self, mock_get_docker_client, cli_runner):
        """Test build command when Docker is not running."""
        mock_get_docker_client.side_effect = SystemExit(1)
        
        result = cli_runner.invoke(build, [])
        
        assert result.exit_code == 1  # Should exit with error
    
    def test_build_command_claude_not_found_removed(self):
        """Test removed - Claude Code check is no longer performed during build."""
        # This test has been removed because the build command no longer checks
        # for Claude Code installation on the host system. Claude Code is installed
        # inside the container during the build process.
        pass
    
    @patch('claude_container.cli.commands.build.get_docker_client')
    def test_build_command_image_exists(self, mock_get_docker_client, cli_runner):
        """Test build command when image already exists."""
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = True
        mock_get_docker_client.return_value = mock_docker
        
        result = cli_runner.invoke(build, [])
        
        assert "already exists. Use --force-rebuild" in result.output
        mock_docker.build_image.assert_not_called()
    
    @patch('claude_container.cli.commands.build.subprocess.check_output')
    @patch('claude_container.cli.commands.build.get_docker_client')
    @patch('claude_container.cli.commands.build.ConfigManager')
    @patch('claude_container.core.dockerfile_generator.DockerfileGenerator')
    def test_build_command_force_rebuild(self, mock_generator_class, mock_config_manager_class,
                                       mock_get_docker_client, mock_subprocess, cli_runner):
        """Test build command with --force-rebuild flag."""
        # Setup git config mocks
        mock_subprocess.side_effect = ["test@example.com", "Test User"]
        
        # Setup mocks
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = True
        mock_get_docker_client.return_value = mock_docker
        
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
            result = cli_runner.invoke(build, ['--force-rebuild'])
        
        # Verify
        assert result.exit_code == 0
        assert "Removing existing image" in result.output
        mock_docker.remove_image.assert_called_once()
        mock_docker.build_image.assert_called_once()
    
    @patch('claude_container.cli.commands.build.subprocess.check_output')
    @patch('claude_container.cli.commands.build.get_docker_client')
    def test_build_command_no_git_config(self, mock_get_docker_client, mock_subprocess, cli_runner):
        """Test build command when git config is not set."""
        # Setup mocks - subprocess raises error when git config not found
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'git config')
        
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = False
        mock_get_docker_client.return_value = mock_docker
        
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
    
    @patch('claude_container.cli.commands.build.subprocess.check_output')
    @patch('claude_container.cli.commands.build.get_docker_client')
    @patch('claude_container.cli.commands.build.ConfigManager')
    @patch('claude_container.core.dockerfile_generator.DockerfileGenerator')
    def test_build_command_moves_dockerignore(self, mock_generator_class, 
                                  mock_config_manager_class, mock_get_docker_client, mock_subprocess, cli_runner):
        """Test that build command temporarily moves .dockerignore file."""
        # Setup git config mocks
        mock_subprocess.side_effect = ["test@example.com", "Test User"]
        
        # Setup mocks
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = False
        mock_get_docker_client.return_value = mock_docker
        
        mock_config_manager = MagicMock()
        mock_config = MagicMock()
        mock_config_manager.get_container_config.return_value = mock_config
        mock_config_manager_class.return_value = mock_config_manager
        
        mock_generator = MagicMock()
        mock_generator.generate_cached.return_value = "FROM python:3.10\nCOPY . /app"
        mock_generator_class.return_value = mock_generator
        
        # Run command with .dockerignore present
        with cli_runner.isolated_filesystem():
            Path(".claude-container").mkdir()
            dockerignore = Path(".dockerignore")
            dockerignore.write_text(".git\nnode_modules\n")
            
            result = cli_runner.invoke(build, [])
            
            # Verify .dockerignore was restored
            assert dockerignore.exists()
            assert dockerignore.read_text() == ".git\nnode_modules\n"
            assert not Path(".dockerignore.claude-backup").exists()
        
        # Verify output mentions moving dockerignore
        assert result.exit_code == 0
        assert "Found .dockerignore - temporarily moving" in result.output
        assert "Restored .dockerignore file" in result.output