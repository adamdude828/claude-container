"""Check Claude permissions command."""

import click
import sys

from claude_container.cli.helpers import get_project_context
from claude_container.core.constants import CLAUDE_SKIP_PERMISSIONS_FLAG, CLAUDE_PERMISSIONS_ERROR, CONTAINER_PREFIX
from claude_container.core.container_runner import ContainerRunner
from claude_container.cli.commands.auth_check import check_claude_auth


@click.command()
def check_permissions():
    """Check if Claude permissions are already accepted.
    
    This command runs a test Claude command with the --dangerously-skip-permissions
    flag to verify if permissions have been accepted.
    """
    # Check if Claude is authenticated
    if not check_claude_auth():
        click.echo("❌ Claude is not authenticated. Please run 'claude-container login' first.", err=True)
        sys.exit(1)
    
    project_root, data_dir = get_project_context()
    
    if not data_dir.exists():
        click.echo("No container found. Please run 'claude-container build' first.", err=True)
        sys.exit(1)
    
    image_name = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
    
    try:
        runner = ContainerRunner(project_root, data_dir, image_name)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    
    click.echo("🔍 Checking permissions status...")
    
    # Try running a simple command with the flag
    try:
        config = runner._get_container_config(
            command=["claude", "-p", "echo test", CLAUDE_SKIP_PERMISSIONS_FLAG],
            tty=False,
            stdin_open=False,
            detach=True,
            remove=False
        )
        
        config['labels'] = {"claude-container": "true", "claude-container-type": "permission-check"}
        
        container = runner.docker_service.run_container(**config)
        result = container.wait()
        exit_code = result.get('StatusCode', 1)
        
        # Get output to check for permission error
        logs = container.logs(stdout=True, stderr=True).decode()
        container.remove()
        
        if exit_code == 0:
            # Also show the output to confirm it worked
            click.echo("✅ Permissions are accepted!")
            click.echo(f"\nTest output: {logs.strip()}")
            click.echo("\nYou can run tasks non-interactively.")
            return
        elif CLAUDE_PERMISSIONS_ERROR in logs:
            # Permissions not accepted
            click.echo("❌ Permissions are NOT accepted.")
            click.echo(f"\nError: {CLAUDE_PERMISSIONS_ERROR}")
            click.echo("\nPlease run 'claude-container accept-permissions' to accept permissions.")
            sys.exit(1)
        else:
            # Some other error
            click.echo("❌ Error checking permissions:", err=True)
            click.echo(logs, err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error checking permissions: {e}", err=True)
        sys.exit(1)