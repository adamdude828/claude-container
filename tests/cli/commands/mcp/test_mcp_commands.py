"""Tests for MCP CLI commands."""

import json
import pytest
from pathlib import Path
from click.testing import CliRunner

from claude_container.cli.commands.mcp import mcp
from claude_container.core.constants import DATA_DIR_NAME, MCP_CONFIG_FILE
from claude_container.utils import MCPManager


class TestMCPCommands:
    """Test MCP CLI commands."""
    
    @pytest.fixture
    def runner(self):
        """Create a Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def temp_project(self, tmp_path, monkeypatch):
        """Create a temporary project directory and change to it."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)
        return project_dir
    
    def test_list_empty(self, runner, temp_project):
        """Test listing when no servers are registered."""
        result = runner.invoke(mcp, ['list'])
        assert result.exit_code == 0
        assert "No MCP servers registered" in result.output
        assert "claude-container mcp add" in result.output
    
    def test_list_with_servers(self, runner, temp_project):
        """Test listing registered servers."""
        # Add some servers first
        manager = MCPManager(temp_project)
        manager.add_server("context7", {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@upstash/context7-mcp"]
        })
        manager.add_server("telemetry", {
            "type": "http",
            "url": "https://mcp.example.com"
        })
        
        result = runner.invoke(mcp, ['list'])
        assert result.exit_code == 0
        assert "context7" in result.output
        assert "telemetry" in result.output
        assert "stdio" in result.output
        assert "http" in result.output
        assert "npx" in result.output
        assert "https://mcp.example.com" in result.output
    
    def test_add_stdio_server(self, runner, temp_project):
        """Test adding a stdio server."""
        config = '{"type": "stdio", "command": "test-cmd", "args": ["arg1", "arg2"]}'
        result = runner.invoke(mcp, ['add', 'test_server', config])
        
        assert result.exit_code == 0
        assert "Added MCP server 'test_server'" in result.output
        
        # Verify it was saved
        manager = MCPManager(temp_project)
        server = manager.get_server("test_server")
        assert server is not None
        assert server.type == "stdio"
        assert server.command == "test-cmd"
        assert server.args == ["arg1", "arg2"]
    
    def test_add_http_server(self, runner, temp_project):
        """Test adding an HTTP server."""
        config = '{"type": "http", "url": "https://test.example.com"}'
        result = runner.invoke(mcp, ['add', 'test_http', config])
        
        assert result.exit_code == 0
        assert "Added MCP server 'test_http'" in result.output
        
        # Verify it was saved
        manager = MCPManager(temp_project)
        server = manager.get_server("test_http")
        assert server is not None
        assert server.type == "http"
        assert server.url == "https://test.example.com"
    
    def test_add_update_existing(self, runner, temp_project):
        """Test updating an existing server."""
        # Add initial server
        manager = MCPManager(temp_project)
        manager.add_server("test", {"type": "stdio", "command": "old-cmd"})
        
        # Update it
        config = '{"type": "stdio", "command": "new-cmd"}'
        result = runner.invoke(mcp, ['add', 'test', config])
        
        assert result.exit_code == 0
        assert "Updated MCP server 'test'" in result.output
        
        # Verify it was updated
        server = manager.get_server("test")
        assert server.command == "new-cmd"
    
    def test_add_from_file(self, runner, temp_project):
        """Test adding server from file."""
        # Create config file
        config_file = temp_project / "server-config.json"
        config_data = {
            "type": "stdio",
            "command": "file-cmd",
            "args": ["file-arg"],
            "env": {"KEY": "value"}
        }
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        result = runner.invoke(mcp, ['add', 'file_server', f'@{config_file}'])
        
        assert result.exit_code == 0
        assert "Added MCP server 'file_server'" in result.output
        
        # Verify it was saved
        manager = MCPManager(temp_project)
        server = manager.get_server("file_server")
        assert server is not None
        assert server.command == "file-cmd"
        assert server.env == {"KEY": "value"}
    
    def test_add_invalid_json(self, runner, temp_project):
        """Test adding with invalid JSON."""
        result = runner.invoke(mcp, ['add', 'test', '{invalid json}'])
        assert result.exit_code == 1
        assert "Invalid JSON configuration" in result.output
    
    def test_add_missing_type(self, runner, temp_project):
        """Test adding without type field."""
        result = runner.invoke(mcp, ['add', 'test', '{"command": "test"}'])
        assert result.exit_code == 1
        assert "Configuration must include 'type' field" in result.output
    
    def test_add_stdio_missing_command(self, runner, temp_project):
        """Test adding stdio server without command."""
        result = runner.invoke(mcp, ['add', 'test', '{"type": "stdio"}'])
        assert result.exit_code == 1
        assert "Stdio servers must include 'command' field" in result.output
    
    def test_add_http_missing_url(self, runner, temp_project):
        """Test adding HTTP server without URL."""
        result = runner.invoke(mcp, ['add', 'test', '{"type": "http"}'])
        assert result.exit_code == 1
        assert "HTTP servers must include 'url' field" in result.output
    
    def test_remove_existing(self, runner, temp_project):
        """Test removing an existing server."""
        # Add a server first
        manager = MCPManager(temp_project)
        manager.add_server("test", {"type": "stdio", "command": "test"})
        
        # Remove it with --yes flag
        result = runner.invoke(mcp, ['remove', 'test', '--yes'])
        
        assert result.exit_code == 0
        assert "Removed MCP server 'test'" in result.output
        
        # Verify it was removed
        assert manager.get_server("test") is None
    
    def test_remove_nonexistent(self, runner, temp_project):
        """Test removing a server that doesn't exist."""
        result = runner.invoke(mcp, ['remove', 'nonexistent', '--yes'])
        assert result.exit_code == 0
        assert "MCP server 'nonexistent' not found" in result.output
    
    def test_remove_with_confirmation(self, runner, temp_project):
        """Test removing with confirmation prompt."""
        # Add a server first
        manager = MCPManager(temp_project)
        manager.add_server("test", {"type": "stdio", "command": "test"})
        
        # Remove with confirmation (simulate 'y' input)
        result = runner.invoke(mcp, ['remove', 'test'], input='y\n')
        
        assert result.exit_code == 0
        assert "Remove MCP server 'test'?" in result.output
        assert "Removed MCP server 'test'" in result.output
    
    def test_remove_cancelled(self, runner, temp_project):
        """Test cancelling removal."""
        # Add a server first
        manager = MCPManager(temp_project)
        manager.add_server("test", {"type": "stdio", "command": "test"})
        
        # Cancel removal (simulate 'n' input)
        result = runner.invoke(mcp, ['remove', 'test'], input='n\n')
        
        assert result.exit_code == 0
        assert "Remove MCP server 'test'?" in result.output
        assert "Cancelled" in result.output
        
        # Verify it wasn't removed
        assert manager.get_server("test") is not None