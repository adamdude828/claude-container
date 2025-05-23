"""Configuration management utilities."""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from ..models.container import ContainerConfig
from ..core.constants import CONFIG_FILE_NAME


class ConfigManager:
    """Manages container configuration."""
    
    def __init__(self, data_dir: Path):
        """Initialize config manager."""
        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True)
        self.config_file = data_dir / CONFIG_FILE_NAME
        self.container_config_file = data_dir / "container_config.json"
    
    def save_config(self, config_type: str = 'claude-generated'):
        """Save container configuration (legacy method for compatibility)."""
        config = {
            'type': config_type,
            'generated_at': datetime.now().isoformat()
        }
        self.config_file.write_text(json.dumps(config, indent=2))
    
    def load_config(self) -> Optional[Dict[str, Any]]:
        """Load container configuration (legacy method for compatibility)."""
        if not self.config_file.exists():
            return None
        try:
            return json.loads(self.config_file.read_text())
        except:
            return None
    
    def save_container_config(self, config: ContainerConfig):
        """Save container configuration."""
        self.container_config_file.write_text(config.model_dump_json(indent=2))
    
    def get_container_config(self) -> Optional[ContainerConfig]:
        """Load container configuration."""
        if not self.container_config_file.exists():
            return None
        try:
            data = json.loads(self.container_config_file.read_text())
            return ContainerConfig(**data)
        except:
            return None
    
    def update_env_vars(self, env_vars: Dict[str, str]):
        """Update environment variables in container config."""
        config = self.get_container_config() or ContainerConfig()
        config.env_vars.update(env_vars)
        self.save_container_config(config)
    
    def add_runtime_version(self, name: str, version: str):
        """Add or update a runtime version."""
        config = self.get_container_config() or ContainerConfig()
        # Remove existing runtime version if present
        config.runtime_versions = [rt for rt in config.runtime_versions if rt.name != name]
        # Add new version
        from ..models.container import RuntimeVersion
        config.runtime_versions.append(RuntimeVersion(name=name, version=version))
        self.save_container_config(config)
    
    def add_custom_command(self, command: str):
        """Add a custom command to the container config."""
        config = self.get_container_config() or ContainerConfig()
        if command not in config.custom_commands:
            config.custom_commands.append(command)
        self.save_container_config(config)