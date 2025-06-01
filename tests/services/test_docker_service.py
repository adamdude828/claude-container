"""Tests for Docker service."""

from unittest.mock import Mock, MagicMock, patch
import pytest
import docker.errors

from claude_container.services.docker_service import DockerService
from claude_container.services.exceptions import (
    DockerServiceError,
    ImageNotFoundError,
    ContainerNotFoundError,
)


class TestDockerService:
    """Test cases for DockerService."""

    @patch('docker.from_env')
    def test_init_success(self, mock_from_env):
        """Test successful initialization."""
        mock_client = Mock()
        mock_client.ping.return_value = None
        mock_from_env.return_value = mock_client

        service = DockerService()
        assert service.client == mock_client
        mock_client.ping.assert_called_once()

    @patch('docker.from_env')
    def test_init_docker_not_running(self, mock_from_env):
        """Test initialization when Docker is not running."""
        mock_from_env.side_effect = docker.errors.DockerException("connection refused")

        with pytest.raises(DockerServiceError, match="Docker daemon is not running"):
            DockerService()

    @patch('docker.from_env')
    def test_init_other_error(self, mock_from_env):
        """Test initialization with other Docker errors."""
        mock_from_env.side_effect = docker.errors.DockerException("Other error")

        with pytest.raises(DockerServiceError, match="Failed to connect to Docker"):
            DockerService()

    @patch('docker.from_env')
    def test_build_image_success(self, mock_from_env):
        """Test successful image build."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_image = Mock()
        mock_logs = [{"stream": "Building..."}, {"stream": "Done"}]
        mock_client.images.build.return_value = (mock_image, mock_logs)

        service = DockerService()
        image, logs = service.build_image(
            path="/test/path",
            dockerfile="Dockerfile",
            tag="test:latest",
            buildargs={"ARG1": "value1"}
        )

        assert image == mock_image
        assert logs == mock_logs
        mock_client.images.build.assert_called_once_with(
            path="/test/path",
            dockerfile="Dockerfile",
            tag="test:latest",
            rm=True,
            nocache=False,
            buildargs={"ARG1": "value1"}
        )

    @patch('docker.from_env')
    def test_build_image_failure(self, mock_from_env):
        """Test image build failure."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.images.build.side_effect = docker.errors.BuildError("Build failed", None)

        service = DockerService()
        with pytest.raises(DockerServiceError, match="Failed to build image"):
            service.build_image("/test/path", "Dockerfile", "test:latest")

    @patch('docker.from_env')
    def test_create_container_success(self, mock_from_env):
        """Test successful container creation."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_container = Mock()
        mock_client.containers.create.return_value = mock_container

        service = DockerService()
        container = service.create_container(
            image="test:latest",
            name="test-container",
            command="echo hello",
            volumes={"/host/path": {"bind": "/container/path", "mode": "rw"}},
            environment={"VAR1": "value1"},
            working_dir="/app",
            labels={"app": "test"}
        )

        assert container == mock_container
        mock_client.containers.create.assert_called_once()

    @patch('docker.from_env')
    def test_create_container_image_not_found(self, mock_from_env):
        """Test container creation with non-existent image."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.containers.create.side_effect = docker.errors.ImageNotFound("Image not found")

        service = DockerService()
        with pytest.raises(ImageNotFoundError, match="Image 'test:latest' not found"):
            service.create_container("test:latest")

    @patch('docker.from_env')
    def test_exec_in_container_success(self, mock_from_env):
        """Test successful command execution in container."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_container = Mock()
        mock_result = Mock()
        mock_container.exec_run.return_value = mock_result

        service = DockerService()
        result = service.exec_in_container(mock_container, "ls -la")

        assert result == mock_result
        mock_container.exec_run.assert_called_once_with(
            "ls -la",
            detach=False,
            stream=False
        )

    @patch('docker.from_env')
    def test_remove_container_success(self, mock_from_env):
        """Test successful container removal."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_container = Mock()

        service = DockerService()
        service.remove_container(mock_container, force=True)

        mock_container.remove.assert_called_once_with(force=True)

    @patch('docker.from_env')
    def test_remove_container_not_found(self, mock_from_env):
        """Test removing non-existent container."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_container = Mock()
        mock_container.remove.side_effect = docker.errors.NotFound("Container not found")

        service = DockerService()
        with pytest.raises(ContainerNotFoundError):
            service.remove_container(mock_container)

    @patch('docker.from_env')
    def test_image_exists_true(self, mock_from_env):
        """Test image_exists returns True when image exists."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.images.get.return_value = Mock()

        service = DockerService()
        assert service.image_exists("test:latest") is True

    @patch('docker.from_env')
    def test_image_exists_false(self, mock_from_env):
        """Test image_exists returns False when image doesn't exist."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.images.get.side_effect = docker.errors.ImageNotFound("Not found")

        service = DockerService()
        assert service.image_exists("test:latest") is False

    @patch('docker.from_env')
    def test_remove_image_success(self, mock_from_env):
        """Test successful image removal."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client

        service = DockerService()
        service.remove_image("test:latest", force=True)

        mock_client.images.remove.assert_called_once_with("test:latest", force=True)

    @patch('docker.from_env')
    def test_remove_image_not_found(self, mock_from_env):
        """Test removing non-existent image."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.images.remove.side_effect = docker.errors.ImageNotFound("Not found")

        service = DockerService()
        with pytest.raises(ImageNotFoundError):
            service.remove_image("test:latest")

    @patch('docker.from_env')
    def test_list_containers_success(self, mock_from_env):
        """Test successful container listing."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_containers = [Mock(), Mock()]
        mock_client.containers.list.return_value = mock_containers

        service = DockerService()
        containers = service.list_containers(
            all=True,
            labels={"app": "test", "env": "prod"}
        )

        assert containers == mock_containers
        mock_client.containers.list.assert_called_once_with(
            all=True,
            filters={"label": ["app=test", "env=prod"]}
        )

    @patch('docker.from_env')
    def test_get_container_success(self, mock_from_env):
        """Test successful container retrieval."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_container = Mock()
        mock_client.containers.get.return_value = mock_container

        service = DockerService()
        container = service.get_container("test-container")

        assert container == mock_container
        mock_client.containers.get.assert_called_once_with("test-container")

    @patch('docker.from_env')
    def test_get_container_not_found(self, mock_from_env):
        """Test getting non-existent container."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.containers.get.side_effect = docker.errors.NotFound("Not found")

        service = DockerService()
        with pytest.raises(ContainerNotFoundError, match="Container 'test-container' not found"):
            service.get_container("test-container")

    @patch('docker.from_env')
    def test_run_container_success(self, mock_from_env):
        """Test successful container run."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_output = b"Hello World"
        mock_client.containers.run.return_value = mock_output

        service = DockerService()
        output = service.run_container(
            "test:latest",
            command="echo Hello World",
            remove=True
        )

        assert output == mock_output
        mock_client.containers.run.assert_called_once_with(
            image="test:latest",
            command="echo Hello World",
            remove=True,
            detach=False
        )

    @patch('docker.from_env')
    def test_run_container_image_not_found(self, mock_from_env):
        """Test running container with non-existent image."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.containers.run.side_effect = docker.errors.ImageNotFound("Not found")

        service = DockerService()
        with pytest.raises(ImageNotFoundError):
            service.run_container("test:latest")

    @patch('docker.from_env')
    @patch('tarfile.open')
    @patch('io.BytesIO')
    def test_copy_to_container_success(self, mock_bytesio, mock_tarfile, mock_from_env):
        """Test successful file copy to container."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_container = Mock()
        mock_tar = MagicMock()
        mock_tarfile.return_value.__enter__.return_value = mock_tar
        mock_stream = Mock()
        mock_bytesio.return_value = mock_stream

        service = DockerService()
        from pathlib import Path
        service.copy_to_container(mock_container, Path("/host/file.txt"), "/container/file.txt")

        mock_tar.add.assert_called_once()
        mock_container.put_archive.assert_called_once()