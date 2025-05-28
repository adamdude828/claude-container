"""Constants used throughout the Claude Container application."""


# Docker-related constants
DEFAULT_WORKDIR = "/workspace"
DEFAULT_BASE_IMAGES = {
    "python": "python:3.11",
    "node": "node:20",
    "default": "ubuntu:22.04"
}

# File patterns for project detection
PROJECT_PATTERNS = {
    "python": ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"],
    "node": ["package.json", "yarn.lock", "package-lock.json"],
    "rust": ["Cargo.toml"],
    "go": ["go.mod"],
}

# Claude Code paths
CLAUDE_CODE_PATHS = [
    '/usr/local/bin/claude',
    '/opt/homebrew/bin/claude',
    '/usr/bin/claude',
    '/Applications/Claude Code.app/Contents/MacOS/Claude Code',
]

# Permission sets
DOCKER_PERMISSIONS = [
    "Bash(docker build*)",
    "Bash(docker run*)",
    "Bash(docker images*)",
    "Bash(docker ps*)",
    "Bash(apt-get*)",
    "Bash(npm*)",
    "Bash(node*)",
    "Read(*)",
    "Write(*)"
]

# Timeout values
BUILD_TIMEOUT = 600  # 10 minutes
DEFAULT_TIMEOUT = 120  # 2 minutes

# Container configuration
CONTAINER_PREFIX = "claude-container"
DATA_DIR_NAME = ".claude-container"
DOCKERFILE_NAME = "Dockerfile.claude"
CONFIG_FILE_NAME = "container_config.json"
SESSIONS_FILE_NAME = "sessions.json"