"""Utilities for finding paths and executables."""

import os
import subprocess
from pathlib import Path
from typing import Optional, List

from ..core.constants import CLAUDE_CODE_PATHS, PROJECT_PATTERNS


class PathFinder:
    """Utility class for finding paths and executables."""
    
    @staticmethod
    def find_claude_code() -> Optional[str]:
        """Try to find Claude Code executable."""
        # Check predefined paths
        for path in CLAUDE_CODE_PATHS:
            if os.path.exists(path):
                return path
        
        # Try which command
        try:
            result = subprocess.run(['which', 'claude'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        # Check in PATH
        for path_dir in os.environ.get('PATH', '').split(':'):
            path = Path(path_dir) / 'claude'
            if path.exists():
                return str(path)
        
        return None
    
    @staticmethod
    def detect_project_type(project_root: Path) -> str:
        """Detect the type of project based on files present."""
        for project_type, patterns in PROJECT_PATTERNS.items():
            for pattern in patterns:
                if (project_root / pattern).exists():
                    return project_type
        return "default"
    
    @staticmethod
    def check_git_ssh_origin(project_root: Path) -> bool:
        """Check if Git remote origin uses SSH."""
        try:
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=project_root,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                origin_url = result.stdout.strip()
                return origin_url.startswith('git@') or 'ssh://' in origin_url
            return True  # No git repo, allow to proceed
        except:
            return True  # If git check fails, allow to proceed