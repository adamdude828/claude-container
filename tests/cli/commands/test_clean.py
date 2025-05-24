import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from click.testing import CliRunner
from claude_container.cli.commands.clean import clean


class TestCleanCommand:
    """Smoke tests for clean command."""
    
    @patch('claude_container.cli.commands.clean.shutil.rmtree')
    @patch('claude_container.cli.commands.clean.DockerClient')
    def test_clean_command_success(self, mock_docker_client_class, mock_rmtree):
        """Test successful clean command."""
        # Setup mock
        mock_docker_client = MagicMock()
        mock_docker_client.image_exists.return_value = True
        mock_docker_client_class.return_value = mock_docker_client
        
        # Run command with isolated filesystem
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create .claude-container directory
            data_dir = Path(".claude-container")
            data_dir.mkdir()
            
            result = runner.invoke(clean, [])
        
        # Verify
        assert result.exit_code == 0
        assert "Cleaned up container resources" in result.output
        mock_docker_client.remove_image.assert_called_once()
        # Check that rmtree was called with .claude-container path
        calls = mock_rmtree.call_args_list
        assert any('.claude-container' in str(call[0][0]) for call in calls)
    
    def test_clean_command_no_data(self):
        """Test clean command when no container data exists."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(clean, [])
        
        assert result.exit_code == 0
        assert "No container data found" in result.output
    
    @patch('claude_container.cli.commands.clean.DockerClient')
    def test_clean_command_docker_not_running(self, mock_docker_client_class):
        """Test clean command when Docker is not running."""
        mock_docker_client_class.side_effect = RuntimeError("Docker daemon is not running")
        
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create .claude-container directory
            data_dir = Path(".claude-container")
            data_dir.mkdir()
            
            result = runner.invoke(clean, [])
        
        assert result.exit_code == 0  # Click doesn't propagate error code from return
        assert "Error: Docker daemon is not running" in result.output
    
    @patch('claude_container.cli.commands.clean.shutil.rmtree')
    @patch('claude_container.cli.commands.clean.DockerClient')
    def test_clean_command_image_not_exists(self, mock_docker_client_class, mock_rmtree):
        """Test clean command when Docker image doesn't exist."""
        # Setup mock
        mock_docker_client = MagicMock()
        mock_docker_client.image_exists.return_value = False
        mock_docker_client_class.return_value = mock_docker_client
        
        # Run command
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create .claude-container directory
            data_dir = Path(".claude-container")
            data_dir.mkdir()
            
            result = runner.invoke(clean, [])
        
        # Verify
        assert result.exit_code == 0
        assert "Cleaned up container resources" in result.output
        mock_docker_client.remove_image.assert_not_called()  # Should not try to remove non-existent image
        # Check that rmtree was called with .claude-container path
        calls = mock_rmtree.call_args_list
        assert any('.claude-container' in str(call[0][0]) for call in calls)
    
    def test_clean_command_help(self):
        """Test clean command help."""
        runner = CliRunner()
        result = runner.invoke(clean, ['--help'])
        
        assert result.exit_code == 0
        assert "Clean up container data and images" in result.output