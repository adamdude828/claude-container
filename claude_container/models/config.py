"""Configuration models for Claude Container."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ToolPermissions:
    """Tool permissions configuration."""
    
    allow: List[str]
    deny: Optional[List[str]] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {"allow": self.allow}
        if self.deny:
            result["deny"] = self.deny
        return result


@dataclass
class ClaudeConfig:
    """Claude configuration model."""
    
    tool_permissions: ToolPermissions
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "toolPermissions": self.tool_permissions.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ClaudeConfig':
        """Create from dictionary."""
        permissions_data = data.get("toolPermissions", {})
        tool_permissions = ToolPermissions(
            allow=permissions_data.get("allow", []),
            deny=permissions_data.get("deny")
        )
        return cls(tool_permissions=tool_permissions)


@dataclass
class ContainerConfig:
    """Container configuration model."""
    
    type: str
    generated_at: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'type': self.type,
            'generated_at': self.generated_at
        }