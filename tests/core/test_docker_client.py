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