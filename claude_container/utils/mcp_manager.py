"""MCP (Model Context Protocol) registry management utilities."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.constants import DATA_DIR_NAME, MCP_CONFIG_FILE
from ..models.mcp import MCPRegistry, MCPServerConfig


class MCPManager:
    """Manages MCP server registry for a project."""

    def __init__(self, project_root: Path):
        """Initialize MCP manager with project root."""
        self.project_root = project_root
        self.config_dir = project_root / DATA_DIR_NAME
        self.config_file = self.config_dir / MCP_CONFIG_FILE

    def load_registry(self) -> MCPRegistry:
        """Load MCP registry from disk."""
        if not self.config_file.exists():
            return MCPRegistry()

        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                return MCPRegistry.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid MCP registry file: {e}")

    def save_registry(self, registry: MCPRegistry) -> None:
        """Save MCP registry to disk."""
        # Ensure directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Save with pretty formatting
        with open(self.config_file, 'w') as f:
            json.dump(registry.model_dump(), f, indent=2)

    def add_server(self, name: str, config: Dict[str, Any]) -> None:
        """Add or update an MCP server configuration."""
        registry = self.load_registry()
        
        # Validate and create server config
        server = MCPServerConfig.model_validate(config)
        registry.mcpServers[name] = server
        
        self.save_registry(registry)

    def remove_server(self, name: str) -> bool:
        """Remove an MCP server configuration. Returns True if removed."""
        registry = self.load_registry()
        
        if name not in registry.mcpServers:
            return False
            
        del registry.mcpServers[name]
        self.save_registry(registry)
        return True

    def list_servers(self) -> List[str]:
        """List all registered server names."""
        registry = self.load_registry()
        return registry.server_names()

    def get_server(self, name: str) -> Optional[MCPServerConfig]:
        """Get a specific server configuration."""
        registry = self.load_registry()
        return registry.mcpServers.get(name)

    def filter_registry(self, names: List[str]) -> MCPRegistry:
        """Get a registry with only the specified servers."""
        registry = self.load_registry()
        return registry.filter_servers(names)

    def validate_server_names(self, names: List[str]) -> List[str]:
        """Validate server names exist and return missing ones."""
        existing = set(self.list_servers())
        requested = set(names)
        return list(requested - existing)