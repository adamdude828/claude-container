# Claude Container Project

## Purpose
Claude Container is a Docker container system for Claude Code that enables:
1. Running Claude Code in isolated Docker environments
2. Submitting background tasks to Claude Code that run asynchronously
3. Automatically generating pull requests when tasks complete
4. Managing both synchronous and asynchronous workflows with a daemon

## Project Status
- **Current State**: Core container infrastructure is complete with unified configuration
- **Recent Updates**:
  1. Implemented unified container configuration system
  2. Fixed interactive shell support for login and run commands
  3. Improved error handling with proper stderr output
- **Next Steps**: 
  1. Implement synchronous task functionality
  2. Add asynchronous task support with daemon

## Key Commands
- `claude-container build` - Build a Docker container with Claude Code
- `claude-container start` - Start a Claude Code session
- `claude-container run` - Run commands in the container
- `claude-container login` - Open interactive shell for Claude authentication
- `claude-container auth-check` - Verify Claude authentication status
- `claude-container task` - Submit background tasks (to be implemented)

## Testing Commands
```bash
# Run lint checks
poetry run ruff check claude_container/

# Run type checks  
poetry run mypy claude_container/

# Check file length limits (max 400 lines)
python scripts/check_file_length.py

# Run tests
poetry run pytest
```

## Architecture Overview
- **CLI Layer**: Command-line interface in `claude_container/cli/`
- **Core Layer**: Docker and container management in `claude_container/core/`
  - `ContainerRunner`: Unified container execution with consistent configuration
  - `DockerClient`: Low-level Docker API wrapper
  - Unified volume mounts and environment variables
- **Models**: Configuration and data models in `claude_container/models/`
- **Utils**: Helper functions in `claude_container/utils/`

### Container Runner Architecture
The `ContainerRunner` class provides unified container configuration:
- **Consistent Volume Mounts**: All commands use the same mounts including:
  - Project directory → `/workspace`
  - `.claude.json` → `/home/node/.claude.json` (read-write)
  - `.claude/` → `/home/node/.claude/` (read-write)
  - `.config/claude/` → `/home/node/.config/claude/` (read-write)
  - SSH, Git, and GitHub CLI configs (read-only)
- **Unified Environment**: Standard environment variables for all containers
- **Execution Modes**:
  - Interactive commands use subprocess for proper TTY handling
  - Non-interactive commands use Docker Python SDK for better output capture

## Known Issues
- Build command reduced to placeholder - needs reimplementation
- Task daemon not yet implemented
- Async task workflow pending

## Fixed Issues
- ✅ Interactive shells now work properly (login, run commands)
- ✅ Error output properly captured and displayed
- ✅ All commands use unified container configuration
- ✅ Claude authentication files properly mounted with read-write access

## Development Workflow
1. Install with poetry: `poetry install`
2. Activate shell: `poetry shell`
3. Make changes and test locally
4. Run lint/type checks before committing

## PR Automation Goal
The ultimate goal is to enable:
```bash
# Submit a background task
claude-container task "Implement feature X"

# Claude works in background
# Automatically creates PR when complete
```