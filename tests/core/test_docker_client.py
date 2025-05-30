import pytest
from unittest.mock import Mock, patch, MagicMock
from claude_container.core.docker_client import DockerClient


class TestDockerClient:
    """Smoke tests for DockerClient functionality."""
    
    @patch('claude_container.core.docker_client.docker.from_env')
    def test_docker_client_initialization_success(self, mock_docker_from_env):
        """Test that DockerClient initializes correctly."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_docker_from_env.return_value = mock_client
        
        docker_client = DockerClient()
        
        assert docker_client.client == mock_client
        mock_docker_from_env.assert_called_once()
        mock_client.ping.assert_called_once()
    
    @patch('claude_container.core.docker_client.docker.from_env')
    def test_docker_client_initialization_daemon_not_running(self, mock_docker_from_env):
        """Test initialization when Docker daemon is not running."""
        from docker.errors import DockerException
        
        mock_client = MagicMock()
        mock_client.ping.side_effect = DockerException("connection refused")
        mock_docker_from_env.return_value = mock_client
        
        with pytest.raises(RuntimeError, match="Docker daemon is not running"):
            DockerClient()
    
    @patch('claude_container.core.docker_client.docker.from_env')
    def test_image_exists_true(self, mock_docker_from_env):
        """Test checking if image exists."""
        mock_client = MagicMock()
        mock_image = Mock()
        mock_client.images.get.return_value = mock_image
        mock_docker_from_env.return_value = mock_client
        
        docker_client = DockerClient()
        result = docker_client.image_exists("test-image:latest")
        
        assert result is True
        mock_client.images.get.assert_called_once_with("test-image:latest")
    
    @patch('claude_container.core.docker_client.docker.from_env')
    def test_image_exists_false(self, mock_docker_from_env):
        """Test checking if image doesn't exist."""
        import docker.errors
        mock_client = MagicMock()
        mock_client.images.get.side_effect = docker.errors.ImageNotFound("Image not found")
        mock_docker_from_env.return_value = mock_client
        
        docker_client = DockerClient()
        result = docker_client.image_exists("nonexistent-image")
        
        assert result is False
    
    @patch('claude_container.core.docker_client.docker.from_env')
    def test_build_image(self, mock_docker_from_env):
        """Test building a Docker image."""
        mock_client = MagicMock()
        mock_image = Mock()
        mock_client.images.build.return_value = (mock_image, [])
        mock_docker_from_env.return_value = mock_client
        
        docker_client = DockerClient()
        result = docker_client.build_image(
            path="/test/path",
            dockerfile="Dockerfile",
            tag="test-tag",
            rm=True,
            nocache=False
        )
        
        mock_client.images.build.assert_called_once_with(
            path="/test/path",
            dockerfile="Dockerfile",
            tag="test-tag",
            rm=True,
            nocache=False
        )
    
    @patch('claude_container.core.docker_client.docker.from_env')
    def test_list_task_containers(self, mock_docker_from_env):
        """Test listing task containers."""
        mock_client = MagicMock()
        mock_container1 = Mock()
        mock_container1.name = "claude-container-task-project1-abc12345"
        mock_container2 = Mock()
        mock_container2.name = "claude-container-task-project1-def67890"
        mock_container3 = Mock()
        mock_container3.name = "other-container"
        
        mock_client.containers.list.return_value = [mock_container1, mock_container2, mock_container3]
        mock_docker_from_env.return_value = mock_client
        
        docker_client = DockerClient()
        
        # Test with project name filter
        containers = docker_client.list_task_containers(project_name="project1")
        mock_client.containers.list.assert_called_with(
            all=True, 
            filters={"label": ["claude-container=true", "claude-container-project=project1"]}
        )
        
        # Test with name prefix filter
        containers = docker_client.list_task_containers(name_prefix="claude-container-task")
        assert len(containers) == 2
        assert mock_container3 not in containers
    
    @patch('claude_container.core.docker_client.docker.from_env')
    def test_cleanup_task_containers(self, mock_docker_from_env):
        """Test cleaning up task containers."""
        mock_client = MagicMock()
        
        # Create mock containers
        mock_container1 = Mock()
        mock_container1.name = "claude-container-task-project1-abc12345"
        mock_container1.status = "exited"
        
        mock_container2 = Mock()
        mock_container2.name = "claude-container-task-project1-def67890"
        mock_container2.status = "running"
        
        mock_client.containers.list.return_value = [mock_container1, mock_container2]
        mock_docker_from_env.return_value = mock_client
        
        docker_client = DockerClient()
        
        # Test cleanup without force (should skip running container)
        removed = docker_client.cleanup_task_containers(project_name="project1", force=False)
        assert removed == 1
        mock_container1.remove.assert_called_once()
        mock_container2.stop.assert_not_called()
        mock_container2.remove.assert_not_called()
        
        # Reset mocks
        mock_container1.remove.reset_mock()
        
        # Test cleanup with force (should stop and remove all)
        removed = docker_client.cleanup_task_containers(project_name="project1", force=True)
        assert removed == 2
        mock_container1.remove.assert_called_once()
        mock_container2.stop.assert_called_once()
        mock_container2.remove.assert_called_once()