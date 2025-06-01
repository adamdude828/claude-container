"""Claude Container - Run Claude Code in isolated Docker environments."""

__version__ = "0.1.0"

# Export main CLI for convenience
from .cli.main import cli

__all__ = ['cli']
