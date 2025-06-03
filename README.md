# Claude Container

A command-line tool for running Claude Code in isolated Docker environments with a universal development container. Test edit.

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

## Requirements

- Docker installed and running
- Python 3.10+
- Claude Code (automatically detected or can be specified with `--claude-code-path`)
- Git repository (preferably with SSH origin for GitHub operations)

## Installation

### For Users

Install Claude Container using pip:

```bash
pip install claude-container
```

### For Development

```bash
# Clone the repository
git clone https://github.com/adamdude828/claude-container.git
cd claude-container

# Install with poetry in development mode
poetry install

# Activate poetry shell (optional)
poetry shell
```

## Quick Start

1. **Navigate to your project directory**:
   ```bash
   cd my-project
   ```

2. **Build a container for your project**:
   ```bash
   claude-container build
   ```

3. **Start a Claude Code session**:
   ```bash
   claude-container start
   ```
   You'll be prompted to describe your task.

4. **Run a command in the container**:
   ```bash
   claude-container run python script.py
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

# Specify Claude Code path if not automatically detected
claude-container build --claude-code-path /path/to/claude
```

### Configure environment variables

Environment variables are stored in the `.claude-container/container_config.json` file and are available inside the container.

```bash
# Set an environment variable
claude-container config env API_KEY your-api-key

# Set a database URL
claude-container config env DATABASE_URL postgres://localhost/mydb
```

### Set runtime versions

Configure specific versions of programming language runtimes.

```bash
# Set Python version
claude-container config runtime python 3.11.10

# Set Node.js version
claude-container config runtime node 20

# Set Go version
claude-container config runtime go 1.23.8
```

### Add custom commands

Add custom commands that will be executed during container build.

```bash
# Install PostgreSQL client
claude-container config add-command "apt-get install -y postgresql-client"

# Install Python packages
claude-container config add-command "pip install pandas numpy"
```

### View configuration

```bash
# Show current configuration
claude-container config show
```

### Run commands in container

Run any command inside the container with your project code mounted.

```bash
# Run Python script
claude-container run python script.py

# Run npm commands
claude-container run npm test

# Start an interactive shell
claude-container run bash
```

### Start Claude Code session

Start a new Claude Code task or continue an existing session.

```bash
# Start a new session (will prompt for description)
claude-container start

# Continue an existing session
claude-container start --continue session-id
```

### Manage sessions

List and manage Claude Code sessions.

```bash
# List all sessions
claude-container sessions list

# Show details of a specific session
claude-container sessions show session-id

# Clean up completed sessions
claude-container sessions clean
```

### Clean up resources

Clean up Docker containers and images created by Claude Container.

```bash
# Remove all Claude Container containers
claude-container clean containers

# Remove all Claude Container images
claude-container clean images

# Remove everything
claude-container clean all
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

### Configuration Options

- **env_vars**: Environment variables available inside the container
- **runtime_versions**: Specific versions of programming languages to install
- **custom_commands**: Custom commands to run during container build
- **base_image**: Base Docker image to use (default: node:20)
- **include_code**: Whether to include code in the image (set to true during build)
- **cached_image_tag**: Tag for the cached image (set during build)

## Available Runtimes

The following runtimes can be configured:

- **Python**: 3.10, 3.11, 3.12, 3.13 (via pyenv)
- **Node.js**: 18, 20, 22 (via nvm)
- **Go**: 1.23.8
- **Rust**: Latest stable
- **Java**: OpenJDK 21
- **Ruby**: System ruby
- **Swift**: 6.1

## Docker Templates

Claude Container uses different Dockerfile templates based on the base image you select:

1. **Node-based images**: Uses a simplified template since Node.js is already available
2. **Ubuntu/Debian-based images**: Uses a full template with apt-get for package installation
3. **Alpine/Python-based images**: Uses a minimal template with alternative package management

All templates ensure that Claude Code is properly installed and configured.

## Troubleshooting

### Docker not running

If you get an error like "Cannot connect to the Docker daemon", make sure Docker is installed and running.

### Claude Code not found

If Claude Code is not automatically detected, specify the path:

```bash
claude-container build --claude-code-path /path/to/claude
```

### GitHub SSH issues

For GitHub operations, make sure your Git repository has an SSH origin:

```bash
git remote set-url origin git@github.com:username/repo.git
```

### Permission errors with GitHub config

If you get permission errors with GitHub CLI config, add `~/.config` to Docker Desktop's file sharing settings.

### Container build failing

If the container build fails, check:
- Docker daemon is running
- You have sufficient disk space
- Your custom commands are valid

### Docker connection refused

- Make sure Docker Desktop is running
- Check Docker status with: `docker info`
- Ensure Docker daemon socket is accessible

## How it Works

Claude Container creates a Docker container based on the Universal Codex Dockerfile with:

1. Node.js 20 LTS pre-installed (required for Claude Code)
2. The Claude Code CLI installed globally
3. Your project code mounted at `/workspace`
4. Custom environment variables and runtime versions configured
5. GitHub CLI configuration mounted for GitHub operations

When you start a Claude Code session, it runs within this container, providing a consistent environment for Claude Code to operate in.

The tool manages permissions for Docker operations within Claude Code, allowing it to make changes to your container configuration when needed.

## Development

### Project Structure

- `claude_container/cli/`: Command-line interface
- `claude_container/core/`: Core functionality for Docker and containers
- `claude_container/models/`: Data models for configuration
- `claude_container/utils/`: Utility functions

### Making Changes

1. Edit code in the `claude_container/` directory
2. Test changes immediately (no reinstall needed with poetry)
3. Run tests: `poetry run pytest` (if tests exist)

## Contributing

Contributions are welcome! Here's how you can contribute:

1. Fork the repository
2. Create a new branch: `git checkout -b my-feature`
3. Make your changes
4. Run tests: `python -m unittest discover`
5. Commit your changes: `git commit -am 'Add new feature'`
6. Push to the branch: `git push origin my-feature`
7. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.