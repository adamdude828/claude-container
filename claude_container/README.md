# Claude Container

Run Claude Code in isolated Docker environments with a universal development container.

## Features

- **Claude Code Pre-installed**: Every container includes Claude Code (requires Node.js 18+)
- **Universal Development Environment**: Based on Node.js 20 LTS by default
- **Project Code Included**: All builds include your project code in `/workspace`
- **No Docker Cache on Force Rebuild**: `--force-rebuild` bypasses Docker's cache completely
- **Project-Based Configuration**: Store environment variables and settings in `.claude-container`
- **Runtime Version Management**: Configure specific versions of Python, Node.js, Go, etc.
- **Custom Build Commands**: Add one-off commands to customize your container

## Installation

```bash
pip install claude-container
```

## Usage

### Build a container for your project

```bash
claude-container build
claude-container build --force-rebuild  # Bypass Docker cache
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