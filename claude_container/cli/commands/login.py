import click
import sys
import subprocess
from pathlib import Path
from claude_container.core.docker_client import DockerClient
from claude_container.core.constants import CONTAINER_PREFIX, DATA_DIR_NAME


@click.command()
def login():
    """Start a container and open a bash shell for Claude authentication.
    
    Since authentication is shared with the host, logging in will
    authenticate Claude globally.
    """
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    if not data_dir.exists():
        click.echo("No container found. Please run 'claude-container build' first.", err=True)
        sys.exit(1)
    
    try:
        docker_client = DockerClient()
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    
    image_name = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
    
    # Check if image exists
    if not docker_client.image_exists(image_name):
        click.echo(f"Container image '{image_name}' not found.", err=True)
        click.echo("Please run 'claude-container build' first.")
        sys.exit(1)
    
    click.echo("Starting container for authentication...")
    
    # Prepare volume mounts (only mount Claude config, not project)
    volumes = {
        str(Path.home() / ".claude"): {"bind": "/root/.claude", "mode": "rw"},
        str(Path.home() / ".config/claude"): {"bind": "/root/.config/claude", "mode": "rw"}
    }
    
    # Add npm cache mount if it exists
    npm_cache = Path.home() / ".npm"
    if npm_cache.exists():
        volumes[str(npm_cache)] = {"bind": "/root/.npm", "mode": "rw"}
    
    click.echo("Opening bash shell for Claude authentication...")
    click.echo("Run 'claude login' to authenticate Claude globally.")
    click.echo("Exit when done (Ctrl+D or 'exit').")
    
    try:
        # Run docker run command directly with subprocess for proper interactive mode
        docker_run_cmd = [
            "docker", "run", "--rm", "-it",
            # Only mount Claude config, not project directory
            "-v", f"{Path.home() / '.claude'}:/root/.claude",
            "-v", f"{Path.home() / '.config/claude'}:/root/.config/claude",
            "-w", "/workspace",
            "-e", "CLAUDE_CONFIG_DIR=/root/.claude",
            "-e", "NODE_OPTIONS=--max-old-space-size=4096",
            "-e", "CODEX_ENV_NODE_VERSION=20",  # Ensure Node.js 20 is configured
            "--label", "claude-container=true",
            "--label", "claude-container-type=login",
        ]
        
        # Add npm cache mount if it exists
        npm_cache = Path.home() / ".npm"
        if npm_cache.exists():
            docker_run_cmd.extend(["-v", f"{npm_cache}:/root/.npm"])
        
        # Mount host's npm global directory for Claude
        try:
            result = subprocess.run(['npm', 'config', 'get', 'prefix'], 
                                  capture_output=True, text=True, check=True)
            npm_prefix = result.stdout.strip()
            if npm_prefix and Path(npm_prefix).exists():
                # Handle spaces in path with temporary symlink
                if ' ' in npm_prefix:
                    temp_link = Path('/tmp/npm-global-link')
                    temp_link.unlink(missing_ok=True)
                    temp_link.symlink_to(npm_prefix)
                    docker_run_cmd.extend(["-v", f"{temp_link}:/host-npm-global:ro"])
                else:
                    docker_run_cmd.extend(["-v", f"{npm_prefix}:/host-npm-global:ro"])
        except:
            # If we can't get npm prefix, claude might not work but login can still proceed
            pass
        
        # Add image - no command specified, will use default CMD or run bash after setup
        docker_run_cmd.append(image_name)
        
        # Run interactively
        subprocess.run(docker_run_cmd)
            
    except Exception as e:
        click.echo(f"Error starting container: {e}", err=True)
        sys.exit(1)