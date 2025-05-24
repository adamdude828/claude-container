import click
import sys
from pathlib import Path
from claude_container.core.docker_client import DockerClient
from claude_container.core.constants import CONTAINER_PREFIX, DATA_DIR_NAME


@click.command()
def auth_check():
    """Check if Claude authentication is still valid.
    
    Starts a new container to verify global Claude authentication status.
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
    
    click.echo("Checking Claude authentication...")
    
    # Prepare volume mounts
    volumes = {
        str(project_root): {"bind": "/home/node/project", "mode": "rw"},
        str(Path.home() / ".claude"): {"bind": "/home/node/.claude", "mode": "rw"},
        str(Path.home() / ".config/claude"): {"bind": "/home/node/.config/claude", "mode": "rw"}
    }
    
    try:
        # Run container with auth check command - need to handle output properly
        container = docker_client.client.containers.run(
            image_name,
            command=["claude", "--model=sonnet", "-p", "Auth check - return immediately"],
            volumes=volumes,
            working_dir="/home/node/project",
            environment={
                'CLAUDE_CONFIG_DIR': '/home/node/.claude',
                'NODE_OPTIONS': '--max-old-space-size=4096'
            },
            detach=True,  # Run detached to get exit code
            labels={"claude-container": "true", "claude-container-type": "auth-check"}
        )
        
        # Wait for container to complete and get exit code
        result = container.wait()
        exit_code = result.get('StatusCode', 1)
        
        # Clean up container
        container.remove()
        
        if exit_code == 0:
            click.echo("✓ Authentication is valid")
        else:
            click.echo("✗ Authentication has expired or is invalid", err=True)
            click.echo("Run 'claude-container login' to re-authenticate")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Error checking authentication: {e}", err=True)
        sys.exit(1)