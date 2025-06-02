"""Models for MCP (Model Context Protocol) configuration."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""

    type: str = Field(..., description="Server type (e.g., 'stdio', 'http')")
    command: Optional[str] = Field(None, description="Command to execute for stdio servers")
    args: Optional[List[str]] = Field(None, description="Arguments for stdio command")
    url: Optional[str] = Field(None, description="URL for http servers")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    # Allow additional fields for future extensibility
    extra: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class MCPRegistry(BaseModel):
    """Registry of MCP servers."""

    mcpServers: Dict[str, MCPServerConfig] = Field(
        default_factory=dict, description="Map of server name to configuration"
    )

    def to_mcp_json(self) -> Dict[str, Any]:
        """Convert to format expected by Claude CLI."""
        servers = {}
        for name, config in self.mcpServers.items():
            server_dict = config.model_dump(exclude_none=True, exclude={"extra"})
            # Merge extra fields at top level
            server_dict.update(config.extra)
            servers[name] = server_dict
        return {"mcpServers": servers}

    def filter_servers(self, names: List[str]) -> "MCPRegistry":
        """Create a new registry with only the specified servers."""
        filtered = {
            name: config
            for name, config in self.mcpServers.items()
            if name in names
        }
        return MCPRegistry(mcpServers=filtered)

    def server_names(self) -> List[str]:
        """Get list of all server names."""
        return list(self.mcpServers.keys())