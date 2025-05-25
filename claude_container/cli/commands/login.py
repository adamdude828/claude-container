import click
import sys
import subprocess
import os
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
    
    # Prepare volume mounts
    volumes = {
        str(project_root): {"bind": "/home/node/project", "mode": "rw"},
        str(Path.home() / ".claude"): {"bind": "/home/node/.claude", "mode": "rw"},
        str(Path.home() / ".config/claude"): {"bind": "/home/node/.config/claude", "mode": "rw"}
    }
    
    # Add npm cache mount if it exists
    npm_cache = Path.home() / ".npm"
    if npm_cache.exists():
        volumes[str(npm_cache)] = {"bind": "/home/node/.npm", "mode": "rw"}
        
    # Mount host's npm global directory (includes Claude binary)
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
                volumes[str(temp_link)] = {'bind': '/host-npm-global', 'mode': 'ro'}
            else:
                volumes[npm_prefix] = {'bind': '/host-npm-global', 'mode': 'ro'}
        else:
            click.echo("Warning: npm prefix directory not found")
    except subprocess.CalledProcessError:
        click.echo("Warning: npm not found or failed to get prefix path")
    except Exception as e:
        click.echo(f"Warning: Failed to setup npm global mount: {e}")
    
    try:
        # Run container with bash
        container = docker_client.client.containers.run(
            image_name,
            command="bash",
            volumes=volumes,
            working_dir="/home/node/project",
            tty=True,
            stdin_open=True,
            detach=True,
            labels={"claude-container": "true", "claude-container-type": "login"},
            environment={
                'CLAUDE_CONFIG_DIR': '/home/node/.claude',
                'NODE_OPTIONS': '--max-old-space-size=4096',
                'ANTHROPIC_API_KEY': os.environ.get('ANTHROPIC_API_KEY', '')
            },
            remove=True  # Auto-remove when done
        )
        
        click.echo("Opening bash shell for Claude authentication...")
        click.echo("Run 'claude login' to authenticate Claude globally.")
        click.echo("Exit when done (Ctrl+D or 'exit').")
        
        # Attach to container interactively
        subprocess.run(["docker", "exec", "-it", container.id, "bash"])
        
        # Stop container when done
        try:
            container.stop()
        except:
            pass  # Container might already be stopped
            
    except Exception as e:
        click.echo(f"Error starting container: {e}", err=True)
        sys.exit(1)