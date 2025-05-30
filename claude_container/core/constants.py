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

# Liberal settings for container environment
LIBERAL_SETTINGS_JSON = """{
  "permissions": {
    "allow": [
      "Bash(npm:*)",
      "Bash(node:*)",
      "Bash(python:*)",
      "Bash(pip:*)",
      "Bash(poetry:*)",
      "Bash(git:*)",
      "Bash(gh:*)",
      "Bash(docker:*)",
      "Bash(grep:*)",
      "Bash(rg:*)",
      "Bash(find:*)",
      "Bash(ls:*)",
      "Bash(cat:*)",
      "Bash(echo:*)",
      "Bash(cd:*)",
      "Bash(pwd:*)",
      "Bash(mkdir:*)",
      "Bash(rm:*)",
      "Bash(cp:*)",
      "Bash(mv:*)",
      "Bash(touch:*)",
      "Bash(chmod:*)",
      "Bash(chown:*)",
      "Bash(curl:*)",
      "Bash(wget:*)",
      "Bash(make:*)",
      "Bash(cmake:*)",
      "Bash(cargo:*)",
      "Bash(go:*)",
      "Bash(yarn:*)",
      "Bash(pnpm:*)",
      "Bash(apt:*)",
      "Bash(apt-get:*)",
      "Bash(brew:*)",
      "Bash(ruff:*)",
      "Bash(mypy:*)",
      "Bash(pytest:*)",
      "Bash(jest:*)",
      "Bash(vitest:*)",
      "Bash(eslint:*)",
      "Bash(prettier:*)",
      "Bash(tsc:*)",
      "Bash(tsx:*)",
      "Bash(bun:*)",
      "Bash(deno:*)",
      "Bash(rustc:*)",
      "Bash(gcc:*)",
      "Bash(g++:*)",
      "Bash(clang:*)",
      "Bash(javac:*)",
      "Bash(java:*)",
      "Bash(dotnet:*)",
      "Bash(ruby:*)",
      "Bash(gem:*)",
      "Bash(bundle:*)",
      "Bash(rails:*)",
      "Bash(php:*)",
      "Bash(composer:*)",
      "Bash(psql:*)",
      "Bash(mysql:*)",
      "Bash(redis-cli:*)",
      "Bash(mongosh:*)",
      "Bash(sqlite3:*)",
      "Bash(terraform:*)",
      "Bash(kubectl:*)",
      "Bash(aws:*)",
      "Bash(gcloud:*)",
      "Bash(az:*)",
      "Bash(heroku:*)",
      "Bash(vercel:*)",
      "Bash(netlify:*)",
      "Bash(npx:*)",
      "Bash(nvm:*)",
      "Bash(pyenv:*)",
      "Bash(rbenv:*)",
      "Bash(export:*)",
      "Bash(source:*)",
      "Bash(which:*)",
      "Bash(whereis:*)",
      "Bash(ps:*)",
      "Bash(kill:*)",
      "Bash(top:*)",
      "Bash(htop:*)",
      "Bash(df:*)",
      "Bash(du:*)",
      "Bash(tar:*)",
      "Bash(zip:*)",
      "Bash(unzip:*)",
      "Bash(sed:*)",
      "Bash(awk:*)",
      "Bash(head:*)",
      "Bash(tail:*)",
      "Bash(sort:*)",
      "Bash(uniq:*)",
      "Bash(wc:*)",
      "Bash(diff:*)",
      "Bash(patch:*)",
      "Bash(ssh:*)",
      "Bash(scp:*)",
      "Bash(rsync:*)",
      "Bash(systemctl:*)",
      "Bash(service:*)",
      "Bash(journalctl:*)",
      "Bash(crontab:*)",
      "Bash(env:*)",
      "Bash(printenv:*)",
      "Bash(date:*)",
      "Bash(whoami:*)",
      "Bash(id:*)",
      "Bash(groups:*)",
      "Bash(su:*)",
      "Bash(sudo:*)",
      "Bash(ln:*)",
      "Bash(basename:*)",
      "Bash(dirname:*)",
      "Bash(realpath:*)",
      "Bash(test:*)",
      "Bash(true:*)",
      "Bash(false:*)",
      "Bash(exit:*)",
      "Read(*)",
      "Write(*)",
      "Edit(*)",
      "MultiEdit(*)",
      "Glob(*)",
      "Grep(*)",
      "LS(*)",
      "NotebookRead(*)",
      "NotebookEdit(*)",
      "WebFetch(*)",
      "TodoRead(*)",
      "TodoWrite(*)",
      "WebSearch(*)",
      "Task(*)"
    ]
  }
}"""