# Claude Container

A CLI utility that wraps Claude Code with Docker to provide isolated environments for running Claude Code locally.

## Prerequisites

- Docker Desktop installed and running
- Python 3.10+
- Poetry (for development)

## Installation

### For Users
```bash
# Install from PyPI (when published)
pip install claude-container

# Or install from source
git clone https://github.com/yourusername/claude-container.git
cd claude-container
pip install .
```

### For Development
```bash
# Clone the repository
git clone https://github.com/yourusername/claude-container.git
cd claude-container

# Install with poetry in development mode
poetry install

# Activate poetry shell (optional)
poetry shell
```

## Usage

### Basic Commands

```bash
# Build container for current project
claude-container build

# Build with custom Dockerfile
claude-container build --dockerfile Dockerfile

# Force rebuild
claude-container build --force-rebuild

# Run command in container
claude-container run -- npm test

# Run interactive session
claude-container run

# Clean up container resources
claude-container clean
```

### Example: Node.js Project

```bash
# Navigate to your project
cd my-nodejs-app

# Build the container (auto-detects Node.js)
claude-container build

# Run your app
claude-container run -- npm start

# Run tests
claude-container run -- npm test
```

### Example: Custom Dockerfile

```bash
# Create a Dockerfile in your project
echo 'FROM node:18-alpine
WORKDIR /app
COPY . .
RUN npm install
CMD ["npm", "start"]' > Dockerfile

# Build with the Dockerfile
claude-container build --dockerfile Dockerfile
```

## Development

### Making Changes

1. Edit code in `claude_container/` directory
2. Test changes immediately (no reinstall needed with poetry)
3. Run tests: `poetry run pytest` (if tests exist)

### Testing Your Changes

```bash
# Test in a sample project
cd /path/to/test/project
poetry run claude-container build
poetry run claude-container run -- your-command
```

## Troubleshooting

### Docker Connection Refused
- Make sure Docker Desktop is running
- Check Docker status: `docker info`

### Build Timeout
- Use `--dockerfile` flag to specify Dockerfile explicitly
- Check if Dockerfile exists in project root

### Container Not Starting
- Check Docker logs: `docker logs <container-name>`
- Ensure your Dockerfile has proper CMD or ENTRYPOINT