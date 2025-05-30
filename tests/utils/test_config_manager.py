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
    
    def test_save_config_legacy(self, temp_project_dir):
        """Test legacy save_config method."""
        import json
        data_dir = temp_project_dir / ".claude-container"
        config_manager = ConfigManager(data_dir)
        
        # Save config
        config_manager.save_config('test-type')
        
        # Verify file exists and contains expected data
        config_file = data_dir / "container_config.json"
        assert config_file.exists()
        
        config_data = json.loads(config_file.read_text())
        assert config_data['type'] == 'test-type'
        assert 'generated_at' in config_data
    
    def test_load_config_legacy(self, temp_project_dir):
        """Test legacy load_config method."""
        data_dir = temp_project_dir / ".claude-container"
        # Create fresh directory to ensure no existing config
        if data_dir.exists():
            import shutil
            shutil.rmtree(data_dir)
        config_manager = ConfigManager(data_dir)
        
        # No config file
        assert config_manager.load_config() is None
        
        # Save and load config
        config_manager.save_config('custom-type')
        loaded = config_manager.load_config()
        assert loaded is not None
        assert loaded['type'] == 'custom-type'
        
        # Test with corrupted config file
        config_file = data_dir / "container_config.json"
        config_file.write_text("invalid json")
        assert config_manager.load_config() is None
    
    def test_get_container_config_corrupted(self, temp_project_dir):
        """Test get_container_config with corrupted file."""
        data_dir = temp_project_dir / ".claude-container"
        config_manager = ConfigManager(data_dir)
        
        # Create corrupted config file
        config_file = data_dir / "container_config.json"
        config_file.write_text("not valid json")
        
        # Should return None on error
        assert config_manager.get_container_config() is None