"""Dockerfile template using Node as base."""

NODE_DOCKERFILE = """FROM node:20

# Build arguments for git configuration
ARG GIT_USER_EMAIL
ARG GIT_USER_NAME

# Install required system packages (minimal for now)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /workspace && \
    mkdir -p /root && \
    chmod 777 /root && \
    mkdir -p /home/node/.ssh && \
    chown -R node:node /home/node && \
    chmod 700 /home/node/.ssh

# Install Claude Code globally in /usr/local so it's available to all users
RUN npm install -g @anthropic-ai/claude-code

# Set up environment variables
ENV HOME=/root

{runtime_overrides}

{env_vars}

{custom_commands}

# Copy project code (always included) with proper ownership
COPY --chown=node:node . /workspace

# Configure git safe directory and user info for both root and node users
RUN git config --global --add safe.directory /workspace && \
    git config --global --add safe.directory '*' && \
    if [ -n "$GIT_USER_EMAIL" ] && [ -n "$GIT_USER_NAME" ]; then \
        git config --global user.email "$GIT_USER_EMAIL" && \
        git config --global user.name "$GIT_USER_NAME" && \
        su - node -c "git config --global user.email '$GIT_USER_EMAIL'" && \
        su - node -c "git config --global user.name '$GIT_USER_NAME'" && \
        su - node -c "git config --global --add safe.directory /workspace" && \
        su - node -c "git config --global --add safe.directory '*'"; \
    fi && \
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
    # Create the base template without COPY command
    base_template = """FROM node:20

# Build arguments for git configuration
ARG GIT_USER_EMAIL
ARG GIT_USER_NAME

# Install required system packages (minimal for now)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /workspace && \
    mkdir -p /root && \
    chmod 777 /root && \
    mkdir -p /home/node/.ssh && \
    chown -R node:node /home/node && \
    chmod 700 /home/node/.ssh

# Install Claude Code globally in /usr/local so it's available to all users
RUN npm install -g @anthropic-ai/claude-code

# Set up environment variables
ENV HOME=/root

{runtime_overrides}

{env_vars}

{custom_commands}

"""
    
    # Add code-specific parts if include_code is True
    if config.include_code:
        code_section = """# Copy project code (always included) with proper ownership
COPY --chown=node:node . /workspace

# Configure git safe directory and user info for both root and node users
RUN git config --global --add safe.directory /workspace && \
    git config --global --add safe.directory '*' && \
    if [ -n "$GIT_USER_EMAIL" ] && [ -n "$GIT_USER_NAME" ]; then \
        git config --global user.email "$GIT_USER_EMAIL" && \
        git config --global user.name "$GIT_USER_NAME" && \
        su - node -c "git config --global user.email '$GIT_USER_EMAIL'" && \
        su - node -c "git config --global user.name '$GIT_USER_NAME'" && \
        su - node -c "git config --global --add safe.directory /workspace" && \
        su - node -c "git config --global --add safe.directory '*'"; \
    fi && \
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

"""
        template = base_template + code_section
    else:
        # For minimal builds, just configure git for the users
        minimal_section = """# Configure git for both root and node users (minimal container)
RUN git config --global --add safe.directory /workspace && \
    git config --global --add safe.directory '*' && \
    if [ -n "$GIT_USER_EMAIL" ] && [ -n "$GIT_USER_NAME" ]; then \
        git config --global user.email "$GIT_USER_EMAIL" && \
        git config --global user.name "$GIT_USER_NAME" && \
        su - node -c "git config --global user.email '$GIT_USER_EMAIL'" && \
        su - node -c "git config --global user.name '$GIT_USER_NAME'" && \
        su - node -c "git config --global --add safe.directory /workspace" && \
        su - node -c "git config --global --add safe.directory '*'"; \
    fi

"""
        template = base_template + minimal_section
    
    # Add the common ending
    template += """# Set working directory
WORKDIR /workspace

# Default command - bash for interactive sessions
CMD ["/bin/bash"]
"""
    
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