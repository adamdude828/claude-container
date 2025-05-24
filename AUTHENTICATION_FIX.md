# Claude Container Authentication Fix

## Problem
Fresh installation of Claude Code in containers doesn't work for authentication. Even with proper config mounts, it fails with "Invalid API key · Please run /login".

## Solution: Mount Claude Code from Host

The ONLY working solution is to mount the host's Claude Code installation into the container.

### Working Configuration (from sandbox tests)

```bash
# Get host's global node_modules directory
NODE_MODULES=$(npm root -g)

# Create temporary symlink to handle spaces in path
TEMP_MODULES="/tmp/node-modules-link"
ln -s "$NODE_MODULES" "$TEMP_MODULES"

# Run container with mounted Claude Code
docker run --rm \
  -v "$TEMP_MODULES":/host-node-modules:ro \
  -v "${HOME}/.claude.json":/home/node/.claude.json:rw \
  -v "${HOME}/.claude":/home/node/.claude:rw \
  -v "$(pwd)":/workspace \
  -e CLAUDE_CONFIG_DIR="/home/node/.claude" \
  -e NODE_OPTIONS="--max-old-space-size=4096" \
  -u node \
  -w /workspace \
  IMAGE_NAME \
  /bin/bash -c '
    # Setup Claude from mounted host installation
    mkdir -p /home/node/.local/bin
    ln -sf /host-node-modules/@anthropic-ai/claude-code/cli.js /home/node/.local/bin/claude
    export PATH="/home/node/.local/bin:$PATH"
    
    # Now claude commands will work with authentication
    claude -p "Hello" --model=opus
  '
```

## Required Changes to Main Project

### 1. Container Runner (`claude_container/core/container_runner.py`)

Add mounting of host's Claude Code:
```python
def _get_volumes(self) -> Dict[str, Dict[str, str]]:
    volumes = {
        str(self.project_root): {'bind': DEFAULT_WORKDIR, 'mode': 'rw'},
    }
    
    # Mount Claude configuration
    claude_config = Path.home() / '.claude.json'
    if claude_config.exists():
        volumes[str(claude_config)] = {'bind': '/home/node/.claude.json', 'mode': 'rw'}
    
    claude_dir = Path.home() / '.claude'
    if claude_dir.exists():
        volumes[str(claude_dir)] = {'bind': '/home/node/.claude', 'mode': 'rw'}
    
    # NEW: Mount host's Claude Code installation
    node_modules = subprocess.run(['npm', 'root', '-g'], 
                                capture_output=True, text=True).stdout.strip()
    if node_modules and Path(node_modules).exists():
        # Handle spaces in path with temporary symlink
        temp_link = Path('/tmp/claude-node-modules-link')
        temp_link.unlink(missing_ok=True)
        temp_link.symlink_to(node_modules)
        volumes[str(temp_link)] = {'bind': '/host-node-modules', 'mode': 'ro'}
    
    return volumes
```

### 2. Dockerfile Template (`claude_container/core/dockerfile_template.py`)

Remove npm install of Claude Code and add setup for mounted version:
```dockerfile
# Remove this:
# RUN npm install -g @anthropic-ai/claude-code

# Add this to entrypoint or startup:
RUN echo '#!/bin/bash\n\
if [ -d "/host-node-modules/@anthropic-ai/claude-code" ]; then\n\
    mkdir -p /home/node/.local/bin\n\
    ln -sf /host-node-modules/@anthropic-ai/claude-code/cli.js /home/node/.local/bin/claude\n\
    export PATH="/home/node/.local/bin:$PATH"\n\
fi\n\
exec "$@"' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

### 3. Environment Setup

Always include:
```python
environment={
    'CLAUDE_CONFIG_DIR': '/home/node/.claude',
    'NODE_OPTIONS': '--max-old-space-size=4096'
}
```

## Key Requirements

1. **Host must have Claude Code installed**: The container depends on the host's installation
2. **Run as node user**: Not root
3. **Mount paths must be to `/home/node/`**: Not `/root/`
4. **Handle spaces in paths**: Use temporary symlinks for macOS paths with spaces
5. **Set PATH correctly**: Include `/home/node/.local/bin` in PATH

## Testing Authentication

Always test with actual API calls:
```bash
claude -p "Hello" --model=opus
```

NOT just version checks:
```bash
claude --version  # This doesn't verify authentication
```