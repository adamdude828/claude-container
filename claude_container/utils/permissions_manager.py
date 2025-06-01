"""Permissions management for Claude Code."""

import json
import shutil
from pathlib import Path
from typing import Optional

from ..core.constants import DOCKER_PERMISSIONS
from ..models.config import ClaudeConfig, ToolPermissions


class PermissionsManager:
    """Manages Claude Code permissions temporarily."""

    def __init__(self):
        """Initialize permissions manager."""
        self.claude_config_path = Path.home() / '.claude.json'
        self.backup_config_path = Path.home() / '.claude.json.backup'
        self.original_config: Optional[str] = None

    def setup_docker_permissions(self):
        """Set up temporary Docker permissions for Claude Code."""
        # Backup existing config if it exists
        if self.claude_config_path.exists():
            self.original_config = self.claude_config_path.read_text()
            shutil.copy2(self.claude_config_path, self.backup_config_path)

        # Create config with Docker permissions
        permissions = self._create_docker_permissions()

        # Write temporary config
        self.claude_config_path.write_text(json.dumps(permissions.to_dict(), indent=2))
        print("Temporarily enabled Docker permissions for Claude Code")

    def restore_permissions(self):
        """Restore original Claude Code permissions."""
        if self.original_config is not None:
            self.claude_config_path.write_text(self.original_config)
            print("Restored original Claude Code configuration")
        elif self.claude_config_path.exists() and not self.backup_config_path.exists():
            # If we created a new config but had no original, remove it
            self.claude_config_path.unlink()
            print("Removed temporary Claude Code configuration")

        # Clean up backup file if it exists
        if self.backup_config_path.exists():
            self.backup_config_path.unlink()

    def _create_docker_permissions(self) -> ClaudeConfig:
        """Create a config with Docker permissions."""
        # Start with Docker permissions
        allow_list = DOCKER_PERMISSIONS.copy()
        deny_list = None

        # If original config exists, merge permissions
        if self.original_config:
            try:
                original_data = json.loads(self.original_config)
                original_config = ClaudeConfig.from_dict(original_data)

                # Merge allow lists
                if original_config.tool_permissions.allow:
                    allow_list.extend(original_config.tool_permissions.allow)
                    # Remove duplicates while preserving order
                    allow_list = list(dict.fromkeys(allow_list))

                # Preserve deny list
                deny_list = original_config.tool_permissions.deny
            except:
                pass  # If parsing fails, use our default config

        tool_permissions = ToolPermissions(allow=allow_list, deny=deny_list)
        return ClaudeConfig(tool_permissions=tool_permissions)
