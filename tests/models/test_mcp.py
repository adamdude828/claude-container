"""Tests for MCP models."""

import pytest
from pydantic import ValidationError

from claude_container.models.mcp import MCPServerConfig, MCPRegistry


class TestMCPServerConfig:
    """Test MCPServerConfig model."""
    
    def test_stdio_server_config(self):
        """Test creating a stdio server configuration."""
        config = MCPServerConfig(
            type="stdio",
            command="npx",
            args=["-y", "@upstash/context7-mcp"]
        )
        
        assert config.type == "stdio"
        assert config.command == "npx"
        assert config.args == ["-y", "@upstash/context7-mcp"]
        assert config.url is None
    
    def test_http_server_config(self):
        """Test creating an HTTP server configuration."""
        config = MCPServerConfig(
            type="http",
            url="https://mcp.example.com"
        )
        
        assert config.type == "http"
        assert config.url == "https://mcp.example.com"
        assert config.command is None
        assert config.args is None
    
    def test_server_config_with_env(self):
        """Test server configuration with environment variables."""
        config = MCPServerConfig(
            type="stdio",
            command="mcp-server",
            env={"API_KEY": "secret"}
        )
        
        assert config.env == {"API_KEY": "secret"}
    
    def test_server_config_extra_fields(self):
        """Test server configuration with extra fields."""
        config = MCPServerConfig(
            type="custom",
            command="custom-server",
            extra={"custom_field": "value"}
        )
        
        assert config.extra == {"custom_field": "value"}
    
    def test_server_config_validation_error(self):
        """Test server configuration validation."""
        with pytest.raises(ValidationError):
            MCPServerConfig()  # Missing required 'type' field


class TestMCPRegistry:
    """Test MCPRegistry model."""
    
    def test_empty_registry(self):
        """Test creating an empty registry."""
        registry = MCPRegistry()
        assert registry.mcpServers == {}
        assert registry.server_names() == []
    
    def test_registry_with_servers(self):
        """Test registry with multiple servers."""
        registry = MCPRegistry(
            mcpServers={
                "context7": MCPServerConfig(
                    type="stdio",
                    command="npx",
                    args=["-y", "@upstash/context7-mcp"]
                ),
                "telemetry": MCPServerConfig(
                    type="http",
                    url="https://mcp.example.com"
                )
            }
        )
        
        assert len(registry.mcpServers) == 2
        assert "context7" in registry.mcpServers
        assert "telemetry" in registry.mcpServers
        assert set(registry.server_names()) == {"context7", "telemetry"}
    
    def test_to_mcp_json(self):
        """Test converting registry to MCP JSON format."""
        registry = MCPRegistry(
            mcpServers={
                "test": MCPServerConfig(
                    type="stdio",
                    command="test-cmd",
                    args=["arg1"],
                    env={"KEY": "value"}
                )
            }
        )
        
        json_data = registry.to_mcp_json()
        
        assert "mcpServers" in json_data
        assert "test" in json_data["mcpServers"]
        assert json_data["mcpServers"]["test"]["type"] == "stdio"
        assert json_data["mcpServers"]["test"]["command"] == "test-cmd"
        assert json_data["mcpServers"]["test"]["args"] == ["arg1"]
        assert json_data["mcpServers"]["test"]["env"] == {"KEY": "value"}
    
    def test_filter_servers(self):
        """Test filtering servers by name."""
        registry = MCPRegistry(
            mcpServers={
                "server1": MCPServerConfig(type="stdio", command="cmd1"),
                "server2": MCPServerConfig(type="stdio", command="cmd2"),
                "server3": MCPServerConfig(type="http", url="http://example.com")
            }
        )
        
        filtered = registry.filter_servers(["server1", "server3"])
        
        assert len(filtered.mcpServers) == 2
        assert "server1" in filtered.mcpServers
        assert "server3" in filtered.mcpServers
        assert "server2" not in filtered.mcpServers
    
    def test_filter_servers_empty(self):
        """Test filtering with no matching servers."""
        registry = MCPRegistry(
            mcpServers={
                "server1": MCPServerConfig(type="stdio", command="cmd1")
            }
        )
        
        filtered = registry.filter_servers(["nonexistent"])
        assert len(filtered.mcpServers) == 0