import pytest
from pathlib import Path
import yaml
from claude_container.utils.config_manager import ConfigManager
from claude_container.models.container import ContainerConfig, RuntimeVersion


class TestConfigManager:
    """Smoke tests for ConfigManager functionality."""
    
    def test_config_manager_initialization(self, temp_project_dir):
        """Test ConfigManager initialization."""
        data_dir = temp_project_dir / ".claude-container"
        manager = ConfigManager(data_dir)
        assert manager.data_dir == data_dir
    
    def test_get_container_config_default(self, temp_project_dir):
        """Test getting container config when none exists."""
        data_dir = temp_project_dir / ".claude-container"
        manager = ConfigManager(data_dir)
        
        config = manager.get_container_config()
        assert config is None
    
    def test_save_and_load_container_config(self, temp_project_dir):
        """Test saving and loading container configuration."""
        data_dir = temp_project_dir / ".claude-container"
        data_dir.mkdir(exist_ok=True)
        manager = ConfigManager(data_dir)
        
        # Create config
        config = ContainerConfig(
            base_image="python:3.11",
            env_vars={"TEST": "value"},
            runtime_versions=[RuntimeVersion(name="python", version="3.11")],
            custom_commands=["pip install requests"]
        )
        
        # Save config
        manager.save_container_config(config)
        
        # Load config
        loaded_config = manager.get_container_config()
        
        assert loaded_config is not None
        assert loaded_config.base_image == "python:3.11"
        assert loaded_config.env_vars == {"TEST": "value"}
        assert len(loaded_config.runtime_versions) == 1
        assert loaded_config.runtime_versions[0].name == "python"
        assert loaded_config.custom_commands == ["pip install requests"]
    
    def test_update_env_vars(self, temp_project_dir):
        """Test updating environment variables."""
        data_dir = temp_project_dir / ".claude-container"
        data_dir.mkdir(exist_ok=True)
        manager = ConfigManager(data_dir)
        
        # Update env vars
        manager.update_env_vars({"KEY1": "value1", "KEY2": "value2"})
        
        # Check config
        config = manager.get_container_config()
        assert config is not None
        assert config.env_vars == {"KEY1": "value1", "KEY2": "value2"}
    
    def test_add_runtime_version(self, temp_project_dir):
        """Test adding runtime version."""
        data_dir = temp_project_dir / ".claude-container"
        data_dir.mkdir(exist_ok=True)
        manager = ConfigManager(data_dir)
        
        # Add runtime
        manager.add_runtime_version("node", "18")
        
        # Check config
        config = manager.get_container_config()
        assert config is not None
        assert len(config.runtime_versions) == 1
        assert config.runtime_versions[0].name == "node"
        assert config.runtime_versions[0].version == "18"
    
    def test_add_custom_command(self, temp_project_dir):
        """Test adding custom command."""
        data_dir = temp_project_dir / ".claude-container"
        data_dir.mkdir(exist_ok=True)
        manager = ConfigManager(data_dir)
        
        # Add command
        manager.add_custom_command("apt-get update")
        
        # Check config
        config = manager.get_container_config()
        assert config is not None
        assert "apt-get update" in config.custom_commands