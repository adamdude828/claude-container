"""Dockerfile generation logic."""

from pathlib import Path

from .dockerfile_template import generate_dockerfile
from ..models.container import ContainerConfig
from ..utils.config_manager import ConfigManager


class DockerfileGenerator:
    """Generates Dockerfiles for Claude Code containers."""
    
    def __init__(self, project_root: Path):
        """Initialize generator."""
        self.project_root = project_root
    
    def generate_with_claude(self, claude_code_path: str) -> str:
        """Generate a Dockerfile using the template system."""
        # Load or create container configuration
        data_dir = self.project_root / ".claude-container"
        config_manager = ConfigManager(data_dir)
        
        # Get container config
        container_config = config_manager.get_container_config()
        if not container_config:
            container_config = ContainerConfig()
        
        # Generate Dockerfile from template
        return generate_dockerfile(container_config)
    
    def generate_cached(self, include_code: bool = True) -> str:
        """Generate a Dockerfile with cached dependencies and optionally include code."""
        data_dir = self.project_root / ".claude-container"
        config_manager = ConfigManager(data_dir)
        
        # Get container config
        container_config = config_manager.get_container_config()
        if not container_config:
            container_config = ContainerConfig()
        
        # Enable code inclusion for cached builds
        container_config.include_code = include_code
        
        # Generate Dockerfile
        return generate_dockerfile(container_config)