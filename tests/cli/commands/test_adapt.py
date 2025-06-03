"""Tests for the adapt command."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from pathlib import Path

from claude_container.cli.commands.adapt import adapt


class TestAdaptCommand:
    """Test the adapt command."""
    
    def test_adapt_with_image(self, mock_config_manager, mock_docker_client):
        """Test adapting an existing Docker image."""
        runner = CliRunner()
        
        # Mock docker client methods
        mock_docker_client.image_exists.return_value = True
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = runner.invoke(adapt, ['--image', 'ubuntu:22.04'])
            
            # Should succeed
            assert result.exit_code == 0
            assert "Using base image: ubuntu:22.04" in result.output
            assert "Successfully created adapted image" in result.output
    
    def test_adapt_with_compose_file(self, mock_config_manager, mock_docker_client, tmp_path):
        """Test adapting from docker-compose file."""
        runner = CliRunner()
        
        # Create a test docker-compose file
        compose_file = tmp_path / "docker-compose.yml"
        compose_content = """
version: '3'
services:
  web:
    build: .
    image: myapp:latest
"""
        compose_file.write_text(compose_content)
        
        with patch('subprocess.run') as mock_run:
            # Mock docker-compose build
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            
            # Mock docker-compose config to return parsed config
            def side_effect(*args, **kwargs):
                if 'config' in args[0]:
                    return Mock(returncode=0, stdout=compose_content)
                return Mock(returncode=0)
            
            mock_run.side_effect = side_effect
            
            result = runner.invoke(adapt, [
                '--compose-file', str(compose_file),
                '--service', 'web'
            ])
            
            assert result.exit_code == 0
            assert "Building from docker-compose service 'web'" in result.output
    
    def test_adapt_missing_arguments(self):
        """Test adapt command with missing arguments."""
        runner = CliRunner()
        
        # No image or compose file
        result = runner.invoke(adapt, [])
        assert result.exit_code == 1
        assert "You must provide either --image or --compose-file" in result.output
        
        # Both image and compose file
        result = runner.invoke(adapt, ['--image', 'ubuntu', '--compose-file', 'docker-compose.yml'])
        assert result.exit_code == 1
        assert "Cannot use both --image and --compose-file" in result.output
        
        # Compose file without service
        result = runner.invoke(adapt, ['--compose-file', 'docker-compose.yml'])
        assert result.exit_code == 1
        assert "--service is required when using --compose-file" in result.output
    
    def test_adapt_pull_image_if_not_exists(self, mock_config_manager, mock_docker_client):
        """Test that adapt pulls image if it doesn't exist locally."""
        runner = CliRunner()
        
        # Mock image doesn't exist
        mock_docker_client.image_exists.return_value = False
        mock_docker_client.docker.images.pull = Mock()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = runner.invoke(adapt, ['--image', 'ubuntu:22.04'])
            
            # Should pull the image
            mock_docker_client.docker.images.pull.assert_called_once_with('ubuntu:22.04')
            assert "Pulling image ubuntu:22.04" in result.output
    
    def test_adapt_custom_tag(self, mock_config_manager, mock_docker_client):
        """Test adapt with custom tag."""
        runner = CliRunner()
        
        mock_docker_client.image_exists.return_value = True
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = runner.invoke(adapt, [
                '--image', 'ubuntu:22.04',
                '--tag', 'my-custom-tag'
            ])
            
            assert result.exit_code == 0
            assert "Successfully created adapted image: my-custom-tag" in result.output
    
    def test_adapt_compose_build_failure(self, mock_config_manager, mock_docker_client, tmp_path):
        """Test handling of docker-compose build failure."""
        runner = CliRunner()
        
        # Create a test docker-compose file
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text("version: '3'\nservices:\n  web:\n    build: .")
        
        with patch('subprocess.run') as mock_run:
            # Mock build failure
            mock_run.return_value = Mock(returncode=1, stderr="Build failed")
            
            result = runner.invoke(adapt, [
                '--compose-file', str(compose_file),
                '--service', 'web'
            ])
            
            assert result.exit_code == 1
            assert "Failed to build service" in result.output
    
    def test_adapt_invalid_compose_file(self, mock_config_manager, mock_docker_client, tmp_path):
        """Test handling of invalid docker-compose file."""
        runner = CliRunner()
        
        # Create an invalid docker-compose file
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text("invalid yaml content {[}")
        
        result = runner.invoke(adapt, [
            '--compose-file', str(compose_file),
            '--service', 'web'
        ])
        
        assert result.exit_code == 1
        assert "Error:" in result.output
    
    def test_adapt_no_cache_option(self, mock_config_manager, mock_docker_client, tmp_path):
        """Test adapt with --no-cache option."""
        runner = CliRunner()
        
        # Create a test docker-compose file
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text("version: '3'\nservices:\n  web:\n    build: .\n    image: test:latest")
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="version: '3'\nservices:\n  web:\n    image: test:latest")
            
            result = runner.invoke(adapt, [
                '--compose-file', str(compose_file),
                '--service', 'web',
                '--no-cache'
            ])
            
            # Verify --no-cache was passed to docker-compose build
            calls = [call for call in mock_run.call_args_list if 'build' in call[0][0]]
            assert any('--no-cache' in call[0][0] for call in calls)