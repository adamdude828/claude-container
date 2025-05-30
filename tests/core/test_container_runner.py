import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from claude_container.core.container_runner import ContainerRunner


class TestContainerRunner:
    """Smoke tests for ContainerRunner functionality."""
    
    @patch('claude_container.core.container_runner.DockerClient')
    def test_container_runner_initialization(self, mock_docker_client_class, temp_project_dir):
        """Test that ContainerRunner initializes correctly."""
        mock_docker = MagicMock()
        mock_docker_client_class.return_value = mock_docker
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        assert runner.project_root == temp_project_dir
        assert runner.data_dir == data_dir
        assert runner.image_name == "test-image"
        assert runner.docker_client == mock_docker
    
    @patch('claude_container.core.container_runner.DockerClient')
    def test_run_command_image_not_exists(self, mock_docker_client_class, temp_project_dir, capsys):
        """Test running command when image doesn't exist."""
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = False
        mock_docker_client_class.return_value = mock_docker
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        runner.run_command(["echo", "hello"])
        
        captured = capsys.readouterr()
        assert "Docker image 'test-image' not found" in captured.out
        assert "Please run 'claude-container build' first" in captured.out
    
    @patch('claude_container.core.container_runner.DockerClient')
    def test_run_command_success(self, mock_docker_client_class, temp_project_dir):
        """Test successful command run."""
        # Setup mocks
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = True
        mock_container = MagicMock()
        mock_container.decode.return_value = "Hello from container"
        mock_docker.client.containers.run.return_value = b"Hello from container"
        mock_docker_client_class.return_value = mock_docker
        
        # Test
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        runner.run_command(["echo", "hello"])
        
        # Verify
        mock_docker.client.containers.run.assert_called_once()
        call_kwargs = mock_docker.client.containers.run.call_args[1]
        assert call_kwargs['working_dir'] == '/workspace'
        assert call_kwargs['remove'] is True
    
    
    @patch('claude_container.core.container_runner.DockerClient')
    def test_create_persistent_container(self, mock_docker_client_class, temp_project_dir):
        """Test creating a persistent container for tasks."""
        # Setup mocks
        mock_docker = MagicMock()
        mock_container = MagicMock()
        mock_docker.client.containers.run.return_value = mock_container
        mock_docker_client_class.return_value = mock_docker
        
        # Test
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        result = runner.create_persistent_container("task")
        
        # Verify
        assert result == mock_container
        mock_docker.client.containers.run.assert_called_once()
        
        # Check configuration
        call_kwargs = mock_docker.client.containers.run.call_args[1]
        assert call_kwargs['command'] == "sleep infinity"
        assert call_kwargs['detach'] is True
        assert call_kwargs['remove'] is False  # Should not auto-remove
        assert call_kwargs['working_dir'] == '/workspace'
        
        # Check container naming pattern
        container_name = call_kwargs['name']
        assert container_name.startswith('claude-container-task-')
        assert temp_project_dir.name.lower() in container_name
        # Should end with 8 character hex suffix
        parts = container_name.split('-')
        assert len(parts[-1]) == 8
        
        # Check labels
        assert call_kwargs['labels'] == {
            "claude-container": "true",
            "claude-container-type": "task",
            "claude-container-project": temp_project_dir.name.lower(),
            "claude-container-prefix": "claude-container"
        }
        
        # Check environment variables
        env = call_kwargs['environment']
        assert env['CLAUDE_CONFIG_DIR'] == '/home/node/.claude'
        assert env['HOME'] == '/home/node'
        assert env['NODE_OPTIONS'] == '--max-old-space-size=4096'