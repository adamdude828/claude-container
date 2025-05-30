"""Tests for config models."""

import pytest
from claude_container.models.config import ToolPermissions, ClaudeConfig, ContainerConfig


class TestConfigModels:
    """Test suite for config models."""
    
    def test_tool_permissions_to_dict_with_deny(self):
        """Test ToolPermissions to_dict with deny list."""
        permissions = ToolPermissions(
            allow=["read", "write"],
            deny=["delete"]
        )
        
        result = permissions.to_dict()
        assert result == {
            "allow": ["read", "write"],
            "deny": ["delete"]
        }
    
    def test_tool_permissions_to_dict_without_deny(self):
        """Test ToolPermissions to_dict without deny list."""
        permissions = ToolPermissions(
            allow=["read", "write"]
        )
        
        result = permissions.to_dict()
        assert result == {"allow": ["read", "write"]}
        assert "deny" not in result
    
    def test_claude_config_to_dict(self):
        """Test ClaudeConfig to_dict method."""
        permissions = ToolPermissions(allow=["all"])
        config = ClaudeConfig(tool_permissions=permissions)
        
        result = config.to_dict()
        assert result == {
            "toolPermissions": {"allow": ["all"]}
        }
    
    def test_claude_config_from_dict(self):
        """Test ClaudeConfig from_dict method."""
        data = {
            "toolPermissions": {
                "allow": ["read", "write"],
                "deny": ["execute"]
            }
        }
        
        config = ClaudeConfig.from_dict(data)
        assert config.tool_permissions.allow == ["read", "write"]
        assert config.tool_permissions.deny == ["execute"]
    
    def test_claude_config_from_dict_minimal(self):
        """Test ClaudeConfig from_dict with minimal data."""
        data = {}
        
        config = ClaudeConfig.from_dict(data)
        assert config.tool_permissions.allow == []
        assert config.tool_permissions.deny is None
    
    def test_container_config_to_dict(self):
        """Test ContainerConfig to_dict method."""
        config = ContainerConfig(
            type="claude-generated",
            generated_at="2024-01-01T12:00:00"
        )
        
        result = config.to_dict()
        assert result == {
            'type': 'claude-generated',
            'generated_at': '2024-01-01T12:00:00'
        }