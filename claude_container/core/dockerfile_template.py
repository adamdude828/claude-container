"""Dockerfile template based on Codex Universal."""

CODEX_UNIVERSAL_DOCKERFILE = """FROM {base_image}

# Ensure Node.js 18+ is available (for node base images)
RUN node_version=$(node --version 2>/dev/null | cut -d'v' -f2 | cut -d'.' -f1) && \\
    if [ -z "$node_version" ] || [ "$node_version" -lt 18 ]; then \\
        echo "Error: Node.js 18+ is required but not found or version too old"; \\
        exit 1; \\
    fi

# Install Claude Code globally with retry and verbose logging
RUN npm config set registry https://registry.npmjs.org/ && \
    npm install -g @anthropic-ai/claude-code --verbose || \
    (echo "Failed to install Claude Code. Retrying..." && \
     npm cache clean --force && \
     npm install -g @anthropic-ai/claude-code --verbose)

# Create .claude directory for configuration
RUN mkdir -p /root/.claude

# Install additional Node.js package managers (yarn already in node:20)
RUN npm install -g pnpm || true

{runtime_overrides}

{env_vars}

{custom_commands}

# Set working directory
WORKDIR /workspace

# Default command
CMD ["claude"]
"""

CODEX_UNIVERSAL_FULL_DOCKERFILE = """FROM {base_image}

# Set up non-interactive frontend
ENV DEBIAN_FRONTEND=noninteractive

# Install essential build tools and libraries
RUN apt-get update && apt-get install -y \\
    build-essential \\
    git \\
    curl \\
    wget \\
    software-properties-common \\
    ca-certificates \\
    gnupg \\
    lsb-release \\
    openssh-client \\
    unzip \\
    zip \\
    jq \\
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 LTS (required for Claude Code)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \\
    apt-get install -y nodejs && \\
    rm -rf /var/lib/apt/lists/*

# Verify Node.js version
RUN node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1) && \\
    if [ "$node_version" -lt 18 ]; then \\
        echo "Error: Node.js 18+ is required but got version $node_version"; \\
        exit 1; \\
    fi

# Install Claude Code globally with retry and verbose logging
RUN npm config set registry https://registry.npmjs.org/ && \
    npm install -g @anthropic-ai/claude-code --verbose || \
    (echo "Failed to install Claude Code. Retrying..." && \
     npm cache clean --force && \
     npm install -g @anthropic-ai/claude-code --verbose)

# Create .claude directory for configuration
RUN mkdir -p /root/.claude

# Install additional Node.js package managers
RUN npm install -g yarn pnpm

# Install Python versions with pyenv
ENV PYENV_ROOT="/root/.pyenv"
ENV PATH="$PYENV_ROOT/bin:$PATH"
RUN curl https://pyenv.run | bash && \\
    eval "$(pyenv init -)" && \\
    pyenv install 3.11.10 && \\
    pyenv global 3.11.10

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:$PATH"

# Install Go
RUN wget -O go.tar.gz https://go.dev/dl/go1.23.8.linux-amd64.tar.gz && \\
    tar -C /usr/local -xzf go.tar.gz && \\
    rm go.tar.gz
ENV PATH="/usr/local/go/bin:$PATH"

# Install Python package managers
RUN pip install --upgrade pip && \\
    pip install poetry uv ruff black mypy

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \\
    chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg && \\
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \\
    apt update && \\
    apt install gh -y && \\
    rm -rf /var/lib/apt/lists/*

{runtime_overrides}

{env_vars}

{custom_commands}

# Set working directory
WORKDIR /workspace

# Default command
CMD ["claude"]
"""

# Minimal template for images that may not have apt-get
MINIMAL_DOCKERFILE = """FROM {base_image}

# Check if Node.js is available and install if needed
RUN if ! command -v node >/dev/null 2>&1; then \\
        echo "Error: Node.js is required but not found in base image"; \\
        echo "Please use a base image with Node.js 18+ or 'node:18' or later"; \\
        exit 1; \\
    fi

# Verify Node.js version
RUN node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1) && \\
    if [ "$node_version" -lt 18 ]; then \\
        echo "Error: Node.js 18+ is required but got version $node_version"; \\
        exit 1; \\
    fi

# Install Claude Code globally with retry and verbose logging
RUN npm config set registry https://registry.npmjs.org/ && \
    npm install -g @anthropic-ai/claude-code --verbose || \
    (echo "Failed to install Claude Code. Retrying..." && \
     npm cache clean --force && \
     npm install -g @anthropic-ai/claude-code --verbose)

# Create .claude directory for configuration
RUN mkdir -p /root/.claude

{runtime_overrides}

{env_vars}

{custom_commands}

# Set working directory
WORKDIR /workspace

# Default command
CMD ["claude"]
"""

def generate_dockerfile(config):
    """Generate Dockerfile from configuration."""
    # Determine which template to use based on base image
    if config.base_image.startswith('node:'):
        # Node base images already have Node.js
        template = CODEX_UNIVERSAL_DOCKERFILE
    elif config.base_image.startswith(('ubuntu:', 'debian:')):
        # Debian-based images can use apt-get
        template = CODEX_UNIVERSAL_FULL_DOCKERFILE
    elif config.base_image.startswith(('alpine:', 'python:3')):
        # Alpine or Python images need minimal template
        template = MINIMAL_DOCKERFILE
    else:
        # Default to full template for unknown base images
        template = CODEX_UNIVERSAL_FULL_DOCKERFILE
    
    # Process runtime overrides
    runtime_overrides = []
    for runtime in config.runtime_versions:
        if runtime.name == "python" and not config.base_image.startswith(('node:', 'python:')):
            runtime_overrides.append(f"RUN pyenv install {runtime.version} && pyenv global {runtime.version}")
        elif runtime.name == "node" and not config.base_image.startswith('node:'):
            runtime_overrides.append(f"RUN . \"$NVM_DIR/nvm.sh\" && nvm install {runtime.version} && nvm alias default {runtime.version}")
        elif runtime.name == "go":
            runtime_overrides.append(f"RUN wget -O go.tar.gz https://go.dev/dl/go{runtime.version}.linux-amd64.tar.gz && \\")
            runtime_overrides.append(f"    tar -C /usr/local -xzf go.tar.gz && rm go.tar.gz")
    
    # Process environment variables
    env_vars = []
    for key, value in config.env_vars.items():
        env_vars.append(f"ENV {key}=\"{value}\"")
    
    # Process custom commands
    custom_commands = []
    for command in config.custom_commands:
        custom_commands.append(f"RUN {command}")
    
    # Include code if requested
    if config.include_code:
        custom_commands.append("# Copy project code")
        custom_commands.append("COPY . /workspace")
    
    return template.format(
        base_image=config.base_image,
        runtime_overrides="\n".join(runtime_overrides) if runtime_overrides else "# No runtime overrides",
        env_vars="\n".join(env_vars) if env_vars else "# No custom environment variables",
        custom_commands="\n".join(custom_commands) if custom_commands else "# No custom commands"
    )