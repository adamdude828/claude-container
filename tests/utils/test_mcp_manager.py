"""Tests for MCP Manager."""

import json
import pytest
from pathlib import Path

from claude_container.utils.mcp_manager import MCPManager
from claude_container.models.mcp import MCPRegistry, MCPServerConfig
from claude_container.core.constants import DATA_DIR_NAME, MCP_CONFIG_FILE


class TestMCPManager:
    """Test MCPManager functionality."""
    
    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        return project_dir
    
    @pytest.fixture
    def mcp_manager(self, temp_project):
        """Create an MCP manager instance."""
        return MCPManager(temp_project)
    
    def test_init(self, mcp_manager, temp_project):
        """Test MCPManager initialization."""
        assert mcp_manager.project_root == temp_project
        assert mcp_manager.config_dir == temp_project / DATA_DIR_NAME
        assert mcp_manager.config_file == temp_project / DATA_DIR_NAME / MCP_CONFIG_FILE
    
    def test_load_empty_registry(self, mcp_manager):
        """Test loading registry when file doesn't exist."""
        registry = mcp_manager.load_registry()
        assert isinstance(registry, MCPRegistry)
        assert len(registry.mcpServers) == 0
    
    def test_save_and_load_registry(self, mcp_manager):
        """Test saving and loading a registry."""
        # Create a registry with servers
        registry = MCPRegistry(
            mcpServers={
                "test_server": MCPServerConfig(
                    type="stdio",
                    command="test-cmd",
                    args=["arg1", "arg2"]
                )
            }
        )
        
        # Save it
        mcp_manager.save_registry(registry)
        
        # Verify file exists
        assert mcp_manager.config_file.exists()
        
        # Load it back
        loaded = mcp_manager.load_registry()
        assert len(loaded.mcpServers) == 1
        assert "test_server" in loaded.mcpServers
        assert loaded.mcpServers["test_server"].command == "test-cmd"
        assert loaded.mcpServers["test_server"].args == ["arg1", "arg2"]
    
    def test_add_server(self, mcp_manager):
        """Test adding a server."""
        config = {
            "type": "http",
            "url": "https://test.example.com"
        }
        
        mcp_manager.add_server("test_http", config)
        
        # Verify it was added
        registry = mcp_manager.load_registry()
        assert "test_http" in registry.mcpServers
        assert registry.mcpServers["test_http"].type == "http"
        assert registry.mcpServers["test_http"].url == "https://test.example.com"
    
    def test_add_server_update_existing(self, mcp_manager):
        """Test updating an existing server."""
        # Add initial server
        mcp_manager.add_server("test", {"type": "stdio", "command": "old-cmd"})
        
        # Update it
        mcp_manager.add_server("test", {"type": "stdio", "command": "new-cmd"})
        
        # Verify it was updated
        registry = mcp_manager.load_registry()
        assert registry.mcpServers["test"].command == "new-cmd"
    
    def test_remove_server(self, mcp_manager):
        """Test removing a server."""
        # Add servers
        mcp_manager.add_server("server1", {"type": "stdio", "command": "cmd1"})
        mcp_manager.add_server("server2", {"type": "stdio", "command": "cmd2"})
        
        # Remove one
        result = mcp_manager.remove_server("server1")
        assert result is True
        
        # Verify it was removed
        registry = mcp_manager.load_registry()
        assert "server1" not in registry.mcpServers
        assert "server2" in registry.mcpServers
    
    def test_remove_nonexistent_server(self, mcp_manager):
        """Test removing a server that doesn't exist."""
        result = mcp_manager.remove_server("nonexistent")
        assert result is False
    
    def test_list_servers(self, mcp_manager):
        """Test listing server names."""
        # Add servers
        mcp_manager.add_server("alpha", {"type": "stdio", "command": "cmd1"})
        mcp_manager.add_server("beta", {"type": "stdio", "command": "cmd2"})
        mcp_manager.add_server("gamma", {"type": "http", "url": "http://test.com"})
        
        servers = mcp_manager.list_servers()
        assert set(servers) == {"alpha", "beta", "gamma"}
    
    def test_get_server(self, mcp_manager):
        """Test getting a specific server."""
        config = {"type": "stdio", "command": "test-cmd", "args": ["arg1"]}
        mcp_manager.add_server("test", config)
        
        server = mcp_manager.get_server("test")
        assert server is not None
        assert server.type == "stdio"
        assert server.command == "test-cmd"
        assert server.args == ["arg1"]
    
    def test_get_nonexistent_server(self, mcp_manager):
        """Test getting a server that doesn't exist."""
        server = mcp_manager.get_server("nonexistent")
        assert server is None
    
    def test_filter_registry(self, mcp_manager):
        """Test filtering registry by server names."""
        # Add servers
        mcp_manager.add_server("server1", {"type": "stdio", "command": "cmd1"})
        mcp_manager.add_server("server2", {"type": "stdio", "command": "cmd2"})
        mcp_manager.add_server("server3", {"type": "http", "url": "http://test.com"})
        
        filtered = mcp_manager.filter_registry(["server1", "server3"])
        
        assert len(filtered.mcpServers) == 2
        assert "server1" in filtered.mcpServers
        assert "server3" in filtered.mcpServers
        assert "server2" not in filtered.mcpServers
    
    def test_validate_server_names(self, mcp_manager):
        """Test validating server names."""
        # Add some servers
        mcp_manager.add_server("existing1", {"type": "stdio", "command": "cmd1"})
        mcp_manager.add_server("existing2", {"type": "stdio", "command": "cmd2"})
        
        # Test validation
        missing = mcp_manager.validate_server_names(["existing1", "nonexistent", "existing2", "missing"])
        assert set(missing) == {"nonexistent", "missing"}
    
    def test_validate_all_valid_names(self, mcp_manager):
        """Test validating when all names are valid."""
        mcp_manager.add_server("server1", {"type": "stdio", "command": "cmd1"})
        mcp_manager.add_server("server2", {"type": "stdio", "command": "cmd2"})
        
        missing = mcp_manager.validate_server_names(["server1", "server2"])
        assert missing == []
    
    def test_invalid_json_file(self, mcp_manager):
        """Test handling invalid JSON in config file."""
        # Create invalid JSON file
        mcp_manager.config_dir.mkdir(parents=True, exist_ok=True)
        with open(mcp_manager.config_file, 'w') as f:
            f.write("{invalid json}")
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Invalid MCP registry file"):
            mcp_manager.load_registry()