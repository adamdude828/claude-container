# Claude Container Project

## Purpose
Claude Container is a Docker container system for Claude Code that enables:
1. Running Claude Code in isolated Docker environments
2. Submitting background tasks to Claude Code that run asynchronously
3. Automatically generating pull requests when tasks complete
4. Managing both synchronous and asynchronous workflows with a daemon

## Project Status
- **Current State**: Build command has been simplified to a placeholder due to issues
- **Next Steps**: 
  1. Implement synchronous task functionality
  2. Add asynchronous task support with daemon

## Key Commands
- `claude-container build` - Build a Docker container with Claude Code
- `claude-container start` - Start a Claude Code session
- `claude-container run` - Run commands in the container
- `claude-container task` - Submit background tasks (to be implemented)

## Testing Commands
```bash
# Run lint checks
poetry run ruff check claude_container/

# Run type checks  
poetry run mypy claude_container/

# Run tests
poetry run pytest
```

## Architecture Overview
- **CLI Layer**: Command-line interface in `claude_container/cli/`
- **Core Layer**: Docker and container management in `claude_container/core/`
- **Models**: Configuration and data models in `claude_container/models/`
- **Utils**: Helper functions in `claude_container/utils/`

## Known Issues
- Build command reduced to placeholder - needs reimplementation
- Task daemon not yet implemented
- Async task workflow pending

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