"""Accept Claude permissions command."""

import click
import sys

from claude_container.cli.helpers import get_project_context
from claude_container.core.constants import CLAUDE_SKIP_PERMISSIONS_FLAG, CLAUDE_PERMISSIONS_ERROR, CONTAINER_PREFIX
from claude_container.core.container_runner import ContainerRunner
from claude_container.cli.commands.auth_check import check_claude_auth


@click.command()
@click.option('--force', is_flag=True, help='Force re-acceptance of permissions')
def accept_permissions(force: bool):
    """Accept Claude permissions for container usage.
    
    This command runs Claude in an interactive session to accept the
    --dangerously-skip-permissions flag, which is required for running
    tasks non-interactively.
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
    
    # Check if permissions are already accepted (unless forced)
    if not force:
        click.echo("🔍 Checking if permissions are already accepted...")
        
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
                click.echo("✅ Permissions are already accepted!")
                return
            elif CLAUDE_PERMISSIONS_ERROR not in logs:
                # Some other error, not permissions-related
                click.echo("❌ Error checking permissions:", err=True)
                click.echo(logs, err=True)
                sys.exit(1)
        except Exception as e:
            click.echo(f"❌ Error checking permissions: {e}", err=True)
            sys.exit(1)
    
    click.echo("🔑 Accepting Claude permissions...")
    click.echo(f"Running: claude {CLAUDE_SKIP_PERMISSIONS_FLAG}")
    click.echo("\nPlease follow the prompts to accept permissions.\n")
    
    # Run Claude interactively to accept permissions
    try:
        # Use the runner's interactive container method
        runner._run_interactive_container(
            ["claude", CLAUDE_SKIP_PERMISSIONS_FLAG]
        )
        
        click.echo("\n✅ Permissions accepted successfully!")
        click.echo("You can now run tasks non-interactively.")
    except Exception as e:
        click.echo(f"❌ Error running Claude: {e}", err=True)
        sys.exit(1)