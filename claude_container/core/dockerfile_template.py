"""Dockerfile template using Node as base."""

NODE_DOCKERFILE = """FROM node:20

# Install required system packages (minimal for now)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Create node user's directories (node user already exists in the base image)
RUN mkdir -p /home/node/.npm-global && \
    mkdir -p /workspace && \
    mkdir -p /root && \
    chmod 777 /root && \
    chown -R node:node /home/node /workspace

# Switch to node user
USER node

# Set up environment variables for node user
ENV NPM_CONFIG_PREFIX=/home/node/.npm-global
ENV PATH="/home/node/.npm-global/bin:$PATH"
ENV HOME=/home/node

# Install Claude Code globally as node user
RUN npm install -g @anthropic-ai/claude-code

{runtime_overrides}

{env_vars}

{custom_commands}

# Copy project code (always included)
COPY --chown=node:node . /workspace

# Configure git safe directory and reset to clean state
USER root
RUN git config --global --add safe.directory /workspace && \
    cd /workspace && \
    if [ -d .git ]; then \
        echo "Cleaning git repository state..." && \
        git reset --hard && \
        git clean -fd && \
        if git show-ref --verify --quiet refs/heads/master; then \
            git checkout master; \
        elif git show-ref --verify --quiet refs/heads/main; then \
            git checkout main; \
        else \
            echo "Warning: Neither master nor main branch found"; \
        fi; \
    fi

# Switch back to node user and configure git for node user too
USER node
RUN git config --global --add safe.directory /workspace

# Set working directory
WORKDIR /workspace

# Default command - bash for interactive sessions
CMD ["/bin/bash"]
"""

# Legacy templates for backward compatibility
CODEX_UNIVERSAL_DOCKERFILE = NODE_DOCKERFILE
CODEX_UNIVERSAL_FULL_DOCKERFILE = NODE_DOCKERFILE

def generate_dockerfile(config):
    """Generate Dockerfile from configuration."""
    # Use the node based template
    template = NODE_DOCKERFILE
    
    # Process runtime overrides - for MVP, we only support Node
    runtime_overrides = []
    for runtime in config.runtime_versions:
        if runtime.name == "node":
            # Node version is controlled by the base image, so just add a comment
            runtime_overrides.append(f"# Node version: {runtime.version} (controlled by base image)")
    
    # Process environment variables
    env_vars = []
    for key, value in config.env_vars.items():
        env_vars.append(f'ENV {key}="{value}"')
    
    # Process custom commands
    custom_commands = []
    for command in config.custom_commands:
        custom_commands.append(f"RUN {command}")
    
    return template.format(
        runtime_overrides="\n".join(runtime_overrides) if runtime_overrides else "# No runtime overrides",
        env_vars="\n".join(env_vars) if env_vars else "# No custom environment variables",
        custom_commands="\n".join(custom_commands) if custom_commands else "# No custom commands"
    )