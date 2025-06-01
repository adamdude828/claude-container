import click
import sys
from claude_container.cli.helpers import get_project_context
from claude_container.core.container_runner import ContainerRunner
from claude_container.core.constants import CONTAINER_PREFIX


def check_claude_auth(quiet=False):
    """Check if Claude authentication is still valid.
    
    Args:
        quiet: If True, only show errors
        
    Returns:
        bool: True if authentication is valid, False otherwise
    """
    project_root, data_dir = get_project_context()
    
    if not data_dir.exists():
        if not quiet:
            click.echo("No container found. Please run 'claude-container build' first.", err=True)
        return False
    
    image_name = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
    
    # Create container runner with unified config
    try:
        runner = ContainerRunner(project_root, data_dir, image_name)
    except RuntimeError as e:
        if not quiet:
            click.echo(f"Error: {e}", err=True)
        return False
    
    # Check if image exists
    if not runner.docker_service.image_exists(image_name):
        if not quiet:
            click.echo(f"Container image '{image_name}' not found.", err=True)
            click.echo("Please run 'claude-container build' first.")
        return False
    
    if not quiet:
        click.echo("Checking Claude authentication...")
    
    try:
        # Use unified container config for auth check
        config = runner._get_container_config(
            command=["claude", "--model=sonnet", "-p", "Auth check - return immediately"],
            tty=False,
            stdin_open=False,
            detach=True,
            remove=False  # We'll remove it manually after getting exit code
        )
        
        # Add labels for tracking
        config['labels'] = {"claude-container": "true", "claude-container-type": "auth-check"}
        
        # Run container
        container = runner.docker_service.run_container(**config)
        
        # Wait for container to complete and get exit code
        result = container.wait()
        exit_code = result.get('StatusCode', 1)
        
        # Clean up container
        container.remove()
        
        if exit_code == 0:
            if not quiet:
                click.echo("✓ Authentication is valid")
            return True
        else:
            if not quiet:
                click.echo("✗ Authentication has expired or is invalid", err=True)
                click.echo("Run 'claude-container login' to re-authenticate")
            return False
            
    except Exception as e:
        if not quiet:
            click.echo(f"Error checking authentication: {e}", err=True)
        return False


@click.command()
def auth_check():
    """Check if Claude authentication is still valid.
    
    Starts a new container to verify global Claude authentication status.
    """
    if not check_claude_auth():
        sys.exit(1)