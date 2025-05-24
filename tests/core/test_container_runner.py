import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from claude_container.core.container_runner import ContainerRunner


class TestContainerRunner:
    """Smoke tests for ContainerRunner functionality."""
    
    @patch('claude_container.core.container_runner.SessionManager')
    @patch('claude_container.core.container_runner.DockerClient')
    def test_container_runner_initialization(self, mock_docker_client_class, mock_session_manager_class, temp_project_dir):
        """Test that ContainerRunner initializes correctly."""
        mock_docker = MagicMock()
        mock_docker_client_class.return_value = mock_docker
        
        mock_session_manager = MagicMock()
        mock_session_manager_class.return_value = mock_session_manager
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        assert runner.project_root == temp_project_dir
        assert runner.data_dir == data_dir
        assert runner.image_name == "test-image"
        assert runner.docker_client == mock_docker
        assert runner.session_manager == mock_session_manager
    
    @patch('claude_container.core.container_runner.SessionManager')
    @patch('claude_container.core.container_runner.DockerClient')
    def test_run_command_image_not_exists(self, mock_docker_client_class, mock_session_manager_class, temp_project_dir, capsys):
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
    
    @patch('claude_container.core.container_runner.SessionManager')
    @patch('claude_container.core.container_runner.DockerClient')
    def test_run_command_success(self, mock_docker_client_class, mock_session_manager_class, temp_project_dir):
        """Test successful command run."""
        # Setup mocks
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = True
        mock_container = MagicMock()
        mock_container.decode.return_value = "Hello from container"
        mock_docker.client.containers.run.return_value = b"Hello from container"
        mock_docker_client_class.return_value = mock_docker
        
        mock_session_manager = MagicMock()
        mock_session_manager_class.return_value = mock_session_manager
        
        # Test
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        runner.run_command(["echo", "hello"])
        
        # Verify
        mock_docker.client.containers.run.assert_called_once()
        call_kwargs = mock_docker.client.containers.run.call_args[1]
        assert call_kwargs['working_dir'] == '/workspace'
        assert call_kwargs['remove'] is True
    
    @patch('claude_container.core.container_runner.SessionManager')
    @patch('claude_container.core.container_runner.DockerClient')
    def test_start_task(self, mock_docker_client_class, mock_session_manager_class, temp_project_dir):
        """Test starting a Claude task."""
        # Setup mocks
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = True
        mock_docker_client_class.return_value = mock_docker
        
        mock_session = MagicMock()
        mock_session.session_id = "session-123"
        mock_session_manager = MagicMock()
        mock_session_manager.create_session.return_value = mock_session
        mock_session_manager_class.return_value = mock_session_manager
        
        # Test
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        runner.start_task("Fix the bug in main.py")
        
        # Verify
        mock_session_manager.create_session.assert_called_once()
        call_args = mock_session_manager.create_session.call_args
        assert call_args[1]['name'] == "Fix the bug in main.py"
        assert call_args[1]['command'] == ['claude', 'Fix the bug in main.py']