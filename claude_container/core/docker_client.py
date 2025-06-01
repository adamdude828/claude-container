"""Docker client wrapper with connection management."""

import docker
from docker.errors import DockerException


class DockerClient:
    """Wrapper for Docker client with automatic connection checking."""

    def __init__(self):
        """Initialize Docker client and test connection."""
        try:
            self.client = docker.from_env()
            # Test connection to Docker daemon
            self.client.ping()
        except DockerException as e:
            if "connection refused" in str(e).lower() or "cannot connect" in str(e).lower():
                raise RuntimeError(
                    "Docker daemon is not running. Please start Docker Desktop or the Docker service."
                ) from e
            else:
                raise RuntimeError(f"Failed to connect to Docker: {e}") from e

    def get_client(self):
        """Get the underlying Docker client."""
        return self.client

    def image_exists(self, image_name: str) -> bool:
        """Check if an image exists."""
        try:
            self.client.images.get(image_name)
            return True
        except docker.errors.ImageNotFound:
            return False

    def remove_image(self, image_name: str, force: bool = True):
        """Remove a Docker image."""
        try:
            self.client.images.remove(image_name, force=force)
            print(f"Removed image: {image_name}")
        except Exception as e:
            print(f"Warning: Could not remove image {image_name}: {e}")

    def build_image(self, path: str, dockerfile: str, tag: str, rm: bool = True, nocache: bool = False, buildargs: dict = None):
        """Build a Docker image."""
        return self.client.images.build(
            path=path,
            dockerfile=dockerfile,
            tag=tag,
            rm=rm,
            nocache=nocache,
            buildargs=buildargs
        )

    def run_container(self, image: str, command: str, **kwargs):
        """Run a Docker container."""
        return self.client.containers.run(image, command, **kwargs)

    def copy_to_container(self, container_id: str, src_path: str, dst_path: str):
        """Copy a file to a container."""
        import io
        import tarfile
        from pathlib import Path

        container = self.client.containers.get(container_id)

        # Create tar archive in memory
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            src_path = Path(src_path)
            tar.add(str(src_path), arcname=dst_path.lstrip('/'))

        tar_stream.seek(0)
        container.put_archive('/', tar_stream.read())

    def list_task_containers(self, name_prefix: str = None, project_name: str = None):
        """List all task containers matching the given criteria.

        Args:
            name_prefix: Container name prefix to filter by
            project_name: Project name to filter by

        Returns:
            List of container objects
        """
        filters = {"label": "claude-container=true"}

        if project_name:
            filters["label"] = [
                "claude-container=true",
                f"claude-container-project={project_name.lower()}"
            ]

        containers = self.client.containers.list(all=True, filters=filters)

        # Further filter by name prefix if provided
        if name_prefix:
            containers = [c for c in containers if c.name.startswith(name_prefix)]

        return containers

    def cleanup_task_containers(self, name_prefix: str = None, project_name: str = None, force: bool = False):
        """Remove task containers matching the given criteria.

        Args:
            name_prefix: Container name prefix to filter by
            project_name: Project name to filter by
            force: Force remove running containers

        Returns:
            Number of containers removed
        """
        containers = self.list_task_containers(name_prefix, project_name)
        removed = 0

        for container in containers:
            try:
                if container.status == 'running' and not force:
                    print(f"Skipping running container: {container.name}")
                    continue

                if container.status == 'running':
                    container.stop()

                container.remove()
                print(f"Removed container: {container.name}")
                removed += 1
            except Exception as e:
                print(f"Failed to remove container {container.name}: {e}")

        return removed
