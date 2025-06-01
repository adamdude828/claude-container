"""Docker service for abstracting Docker operations."""

import io
import logging
import tarfile
from pathlib import Path
from typing import Any, Optional

import docker
import docker.errors
from docker.models.containers import Container
from docker.models.images import Image

from .exceptions import (
    ContainerNotFoundError,
    DockerServiceError,
    ImageNotFoundError,
)

logger = logging.getLogger(__name__)


class DockerService:
    """Service for Docker operations with clean abstractions."""

    def __init__(self):
        """Initialize Docker service and test connection."""
        try:
            self.client = docker.from_env()
            self.client.ping()
        except docker.errors.DockerException as e:
            if "connection refused" in str(e).lower() or "cannot connect" in str(e).lower():
                raise DockerServiceError(
                    "Docker daemon is not running. Please start Docker Desktop or the Docker service."
                ) from e
            else:
                raise DockerServiceError(f"Failed to connect to Docker: {e}") from e

    def build_image(
        self,
        path: str,
        dockerfile: str,
        tag: str,
        rm: bool = True,
        nocache: bool = False,
        buildargs: Optional[dict[str, str]] = None,
    ) -> tuple[Image, list[dict[str, Any]]]:
        """Build a Docker image.

        Args:
            path: Path to the build context
            dockerfile: Path to the Dockerfile relative to the build context
            tag: Tag for the image
            rm: Remove intermediate containers after build
            nocache: Do not use cache when building
            buildargs: Build arguments

        Returns:
            Tuple of (built image, build logs)

        Raises:
            DockerServiceError: If build fails
        """
        try:
            image, logs = self.client.images.build(
                path=path,
                dockerfile=dockerfile,
                tag=tag,
                rm=rm,
                nocache=nocache,
                buildargs=buildargs or {},
            )
            return image, list(logs)
        except docker.errors.BuildError as e:
            raise DockerServiceError(f"Failed to build image: {e}") from e
        except Exception as e:
            raise DockerServiceError(f"Unexpected error building image: {e}") from e

    def create_container(
        self,
        image: str,
        name: Optional[str] = None,
        command: Optional[str] = None,
        volumes: Optional[dict[str, dict[str, str]]] = None,
        environment: Optional[dict[str, str]] = None,
        working_dir: Optional[str] = None,
        labels: Optional[dict[str, str]] = None,
        **kwargs,
    ) -> Container:
        """Create a Docker container.

        Args:
            image: Image name
            name: Container name
            command: Command to run
            volumes: Volume mappings
            environment: Environment variables
            working_dir: Working directory
            labels: Container labels
            **kwargs: Additional Docker run parameters

        Returns:
            Created container object

        Raises:
            ImageNotFoundError: If image not found
            DockerServiceError: If creation fails
        """
        try:
            container = self.client.containers.create(
                image=image,
                name=name,
                command=command,
                volumes=volumes,
                environment=environment,
                working_dir=working_dir,
                labels=labels,
                **kwargs,
            )
            return container
        except docker.errors.ImageNotFound as e:
            raise ImageNotFoundError(f"Image '{image}' not found") from e
        except docker.errors.APIError as e:
            raise DockerServiceError(f"Failed to create container: {e}") from e
        except Exception as e:
            raise DockerServiceError(f"Unexpected error creating container: {e}") from e

    def exec_in_container(
        self,
        container: Container,
        command: str,
        detach: bool = False,
        stream: bool = False,
        **kwargs,
    ) -> Any:
        """Execute a command in a running container.

        Args:
            container: Container object
            command: Command to execute
            detach: Run in background
            stream: Stream output
            **kwargs: Additional exec parameters

        Returns:
            Command output or exit code

        Raises:
            ContainerNotFoundError: If container not found
            DockerServiceError: If execution fails
        """
        try:
            return container.exec_run(
                command,
                detach=detach,
                stream=stream,
                **kwargs,
            )
        except docker.errors.NotFound as e:
            raise ContainerNotFoundError("Container not found") from e
        except docker.errors.APIError as e:
            raise DockerServiceError(f"Failed to execute in container: {e}") from e
        except Exception as e:
            raise DockerServiceError(f"Unexpected error executing in container: {e}") from e

    def remove_container(self, container: Container, force: bool = False) -> None:
        """Remove a container.

        Args:
            container: Container object
            force: Force remove even if running

        Raises:
            ContainerNotFoundError: If container not found
            DockerServiceError: If removal fails
        """
        try:
            container.remove(force=force)
        except docker.errors.NotFound as e:
            raise ContainerNotFoundError("Container not found") from e
        except docker.errors.APIError as e:
            raise DockerServiceError(f"Failed to remove container: {e}") from e
        except Exception as e:
            raise DockerServiceError(f"Unexpected error removing container: {e}") from e

    def image_exists(self, image_name: str) -> bool:
        """Check if an image exists.

        Args:
            image_name: Name of the image

        Returns:
            True if image exists, False otherwise
        """
        try:
            self.client.images.get(image_name)
            return True
        except docker.errors.ImageNotFound:
            return False
        except Exception as e:
            logger.warning(f"Error checking image existence: {e}")
            return False

    def remove_image(self, image_name: str, force: bool = True) -> None:
        """Remove a Docker image.

        Args:
            image_name: Name of the image
            force: Force removal

        Raises:
            ImageNotFoundError: If image not found
            DockerServiceError: If removal fails
        """
        try:
            self.client.images.remove(image_name, force=force)
        except docker.errors.ImageNotFound as e:
            raise ImageNotFoundError(f"Image '{image_name}' not found") from e
        except docker.errors.APIError as e:
            raise DockerServiceError(f"Failed to remove image: {e}") from e
        except Exception as e:
            raise DockerServiceError(f"Unexpected error removing image: {e}") from e

    def copy_to_container(
        self, container: Container, src_path: Path, dst_path: str
    ) -> None:
        """Copy a file to a container.

        Args:
            container: Container object
            src_path: Source file path
            dst_path: Destination path in container

        Raises:
            ContainerNotFoundError: If container not found
            DockerServiceError: If copy fails
        """
        try:
            # Create tar archive in memory
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                tar.add(str(src_path), arcname=dst_path.lstrip('/'))

            tar_stream.seek(0)
            container.put_archive('/', tar_stream.read())
        except docker.errors.NotFound as e:
            raise ContainerNotFoundError("Container not found") from e
        except Exception as e:
            raise DockerServiceError(f"Failed to copy to container: {e}") from e

    def list_containers(
        self,
        all: bool = True,
        filters: Optional[dict[str, Any]] = None,
        labels: Optional[dict[str, str]] = None,
    ) -> list[Container]:
        """List containers with optional filters.

        Args:
            all: Include stopped containers
            filters: Docker filters
            labels: Label filters

        Returns:
            List of containers

        Raises:
            DockerServiceError: If listing fails
        """
        try:
            filter_dict = filters or {}
            if labels:
                filter_dict['label'] = [f"{k}={v}" for k, v in labels.items()]

            return self.client.containers.list(all=all, filters=filter_dict)
        except docker.errors.APIError as e:
            raise DockerServiceError(f"Failed to list containers: {e}") from e
        except Exception as e:
            raise DockerServiceError(f"Unexpected error listing containers: {e}") from e

    def get_container(self, container_id: str) -> Container:
        """Get a container by ID or name.

        Args:
            container_id: Container ID or name

        Returns:
            Container object

        Raises:
            ContainerNotFoundError: If container not found
            DockerServiceError: If retrieval fails
        """
        try:
            return self.client.containers.get(container_id)
        except docker.errors.NotFound as e:
            raise ContainerNotFoundError(
                f"Container '{container_id}' not found"
            ) from e
        except docker.errors.APIError as e:
            raise DockerServiceError(f"Failed to get container: {e}") from e
        except Exception as e:
            raise DockerServiceError(f"Unexpected error getting container: {e}") from e

    def run_container(
        self,
        image: str,
        command: Optional[str] = None,
        remove: bool = True,
        detach: bool = False,
        **kwargs,
    ) -> Any:
        """Run a container and return output or container object.

        Args:
            image: Image name
            command: Command to run
            remove: Remove container after run
            detach: Run in background
            **kwargs: Additional Docker run parameters

        Returns:
            Container output (if not detached) or Container object (if detached)

        Raises:
            ImageNotFoundError: If image not found
            DockerServiceError: If run fails
        """
        try:
            return self.client.containers.run(
                image=image,
                command=command,
                remove=remove,
                detach=detach,
                **kwargs,
            )
        except docker.errors.ImageNotFound as e:
            raise ImageNotFoundError(f"Image '{image}' not found") from e
        except docker.errors.ContainerError as e:
            raise DockerServiceError(f"Container exited with error: {e}") from e
        except docker.errors.APIError as e:
            raise DockerServiceError(f"Failed to run container: {e}") from e
        except Exception as e:
            raise DockerServiceError(f"Unexpected error running container: {e}") from e
