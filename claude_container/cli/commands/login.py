import click
import sys
from claude_container.cli.helpers import get_project_context, ensure_container_built
from claude_container.core.container_runner import ContainerRunner
from claude_container.core.constants import CONTAINER_PREFIX


@click.command()
def login():
    """Start a container and open a bash shell for Claude authentication.
    
    Since authentication is shared with the host, logging in will
    authenticate Claude globally.
    """
    project_root, data_dir = get_project_context()
    ensure_container_built(data_dir)
    
    image_name = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
    
    # Create container runner with unified config
    try:
        runner = ContainerRunner(project_root, data_dir, image_name)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    
    # Check if image exists
    if not runner.docker_service.image_exists(image_name):
        click.echo(f"Container image '{image_name}' not found.", err=True)
        click.echo("Please run 'claude-container build' first.")
        sys.exit(1)
    
    click.echo("Starting container for authentication...")
    click.echo("Opening bash shell for Claude authentication...")
    click.echo("Run 'claude login' to authenticate Claude globally.")
    click.echo("Exit when done (Ctrl+D or 'exit').")
    
    try:
        # Use the run_command method which uses unified config
        # This will mount all necessary volumes including .claude.json with rw permissions
        runner.run_command(['/bin/bash'], user='node')
            
    except Exception as e:
        click.echo(f"Error starting container: {e}", err=True)
        sys.exit(1)