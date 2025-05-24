# Claude Container

A command-line tool for running Claude Code in isolated Docker environments with a universal development container.

## What is Claude Container?

Claude Container is a CLI tool that helps developers use [Claude Code](https://www.anthropic.com/claude-code) within a consistent, isolated Docker environment. It provides a simple way to:

1. Create Docker containers with Claude Code pre-installed
2. Configure development environments with specific runtime versions
3. Store environment variables and settings on a per-project basis
4. Run Claude Code tasks in an isolated environment
5. Execute commands within the container

This eliminates the "works on my machine" problem and ensures a consistent development experience across team members while using Claude Code.

## Features

- **Claude Code Pre-installed**: Every container includes Claude Code (requires Node.js 18+)
- **Universal Development Environment**: Based on Node.js 20 LTS by default
- **Project Code Included**: All builds include your project code in `/workspace`
- **No Docker Cache on Force Rebuild**: `--force-rebuild` bypasses Docker's cache completely
- **Project-Based Configuration**: Store environment variables and settings in `.claude-container`
- **Runtime Version Management**: Configure specific versions of Python, Node.js, Go, etc.
- **Custom Build Commands**: Add one-off commands to customize your container
- **GitHub CLI Integration**: Automatically mounts GitHub CLI configuration for seamless GitHub operations
- **Session Management**: Create and continue Claude Code sessions

## Installation

```bash
pip install claude-container
```

## Usage

### Build a container for your project

```bash
# Build with default settings
claude-container build

# Force rebuild (bypasses Docker cache)
claude-container build --force-rebuild

# Specify a custom tag
claude-container build --tag my-custom-tag
```

### Configure environment variables

```bash
claude-container config env API_KEY your-api-key
claude-container config env DATABASE_URL postgres://localhost/mydb
```

### Set runtime versions

```bash
claude-container config runtime python 3.11.10
claude-container config runtime node 20
```

### Add custom commands

```bash
claude-container config add-command "apt-get install -y postgresql-client"
claude-container config add-command "pip install pandas numpy"
```

### View configuration

```bash
claude-container config show
```


### Run commands in container

```bash
claude-container run python script.py
claude-container run npm test
```

### Start Claude Code session

```bash
claude-container start "implement new feature"
```

## Configuration

Configuration is stored in `.claude-container/container_config.json`:

```json
{
  "env_vars": {
    "API_KEY": "your-api-key",
    "DATABASE_URL": "postgres://localhost/mydb"
  },
  "runtime_versions": [
    {"name": "python", "version": "3.11.10"},
    {"name": "node", "version": "20"}
  ],
  "custom_commands": [
    "apt-get install -y postgresql-client"
  ],
  "base_image": "node:20",
  "include_code": false,
  "cached_image_tag": null
}
```

## Available Runtimes

- **Python**: 3.10, 3.11, 3.12, 3.13 (via pyenv)
- **Node.js**: 18, 20, 22 (via nvm)
- **Go**: 1.23.8
- **Rust**: Latest stable
- **Java**: OpenJDK 21
- **Ruby**: System ruby
- **Swift**: 6.1

## Commands

- `build`: Build Docker container with project code included
  - `--force-rebuild`: Force rebuild without Docker cache
  - `--tag`: Custom image tag
- `run`: Run command in container
- `start`: Start Claude Code session
- `sessions`: Manage Claude Code sessions
- `clean`: Clean up containers and images
- `config`: Manage container configuration
  - `env`: Set environment variable
  - `runtime`: Set runtime version
  - `add-command`: Add custom build command
  - `show`: Display configuration
  - `reset`: Reset to defaults