# Codex-Universal Refactor Summary

## Changes Made

### 1. Dockerfile Template Refactored
- Replaced custom Ubuntu-based Dockerfile with `ghcr.io/openai/codex-universal:latest`
- Removed all manual runtime installations (Python via pyenv, Go, Rust, etc.)
- These are now pre-installed in codex-universal

### 2. User Changes
- Changed from 'node' user to 'claude' user throughout the codebase
- Updated all mount paths from `/home/node` to `/home/claude`

### 3. Language Version Configuration
- Using codex-universal environment variables:
  - `CODEX_ENV_PYTHON_VERSION=3.11`
  - `CODEX_ENV_NODE_VERSION=20`
  - `CODEX_ENV_GO_VERSION=1.23`
  - `CODEX_ENV_RUST_VERSION=1.83`

### 4. Benefits
- **Faster builds**: No more compiling Python from source
- **Smaller Dockerfile**: Removed hundreds of lines of installation code
- **Pre-installed tools**: Python, Node.js, Go, Rust, Ruby, Java, Swift all included
- **Better caching**: Base image is cached by Docker

### 5. What's Preserved
- Claude wrapper script functionality
- Project code copying to `/workspace`
- Volume mounting for Claude configuration
- Git safe directory configuration

## Testing the New Build

```bash
# Clean build
claude-container build --force-rebuild

# The build should be MUCH faster now!
```

## Notes
- The `base_image` configuration in ContainerConfig is now ignored
- All language runtimes are pre-installed in codex-universal
- No need for apt-get installations or manual downloads