"""Docker image building functionality."""

import shutil
from pathlib import Path
from typing import Optional

from .docker_client import DockerClient
from .dockerfile_generator import DockerfileGenerator
from ..utils.permissions_manager import PermissionsManager
from ..utils.config_manager import ConfigManager
from ..core.constants import DOCKERFILE_NAME, CONTAINER_PREFIX


class ImageBuilder:
    """Handles Docker image building with Claude Code."""
    
    def __init__(self, project_root: Path, data_dir: Path):
        """Initialize image builder."""
        self.project_root = project_root
        self.data_dir = data_dir
        self.docker_client = DockerClient()
        self.dockerfile_generator = DockerfileGenerator(project_root)
        self.config_manager = ConfigManager(data_dir)
        self.image_name = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
    
    def build(self, claude_code_path: str, force_rebuild: bool = False) -> str:
        """Build Docker image using Claude Code."""
        # Check if rebuild is needed
        if not force_rebuild and self.docker_client.image_exists(self.image_name):
            return self.image_name
        
        # Remove existing image if force rebuild
        if force_rebuild and self.docker_client.image_exists(self.image_name):
            self.docker_client.remove_image(self.image_name)
        
        # Set up permissions and generate Dockerfile
        permissions_manager = PermissionsManager()
        temp_dockerfile = self.data_dir / DOCKERFILE_NAME
        
        try:
            # Set up Docker permissions
            permissions_manager.setup_docker_permissions()
            
            # Generate Dockerfile with Claude
            dockerfile_content = self.dockerfile_generator.generate_with_claude(
                claude_code_path
            )
            
            # Write Dockerfile
            temp_dockerfile.write_text(dockerfile_content)
            
            # Build image
            self._build_image(temp_dockerfile)
            
            # Save configuration
            self.config_manager.save_config()
            
            # Clean up Dockerfile on success
            if temp_dockerfile.exists():
                temp_dockerfile.unlink()
            
            return self.image_name
            
        except Exception as e:
            print(f"Build failed. Dockerfile saved at: {temp_dockerfile}")
            raise
        finally:
            # Always restore permissions
            permissions_manager.restore_permissions()
    
    def _build_image(self, dockerfile_path: Path):
        """Build Docker image from Dockerfile."""
        self.docker_client.build_image(
            path=str(self.project_root),
            dockerfile=str(dockerfile_path),
            tag=self.image_name,
            rm=True
        )