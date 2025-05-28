"""Run async command for Claude Container."""

import click
from pathlib import Path
from datetime import datetime

from ...core.docker_client import DockerClient
from ...core.container_runner import ContainerRunner
from ...core.constants import DATA_DIR_NAME, CONTAINER_PREFIX
from ...utils.session_manager import SessionManager


@click.command(context_settings=dict(ignore_unknown_options=True))
@click.argument('command', nargs=-1, type=click.UNPROCESSED)
@click.option('--name', help='Name for this async session')
def run_async(command, name):
    """Run command asynchronously in the background container"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    if not data_dir.exists():
        click.echo("No container found. Please run 'build' first.")
        return
    
    try:
        # Initialize Docker client (checks connection)
        docker_client = DockerClient()
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        return
    
    image_name = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
    
    # Generate session name if not provided
    if not name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"session_{timestamp}"
    
    # Create session
    session_manager = SessionManager(data_dir)
    session = session_manager.create_session(name, list(command))
    
    click.echo(f"Starting async session: {name}")
    click.echo(f"Session ID: {session.session_id}")
    
    # For claude commands, add --dangerously-skip-permissions flag for async execution
    cmd_list = list(command)
    if cmd_list and cmd_list[0] == 'claude' and '--dangerously-skip-permissions' not in cmd_list:
        # Insert --dangerously-skip-permissions after 'claude' but before other args
        cmd_list.insert(1, '--dangerously-skip-permissions')
    
    # Run the command asynchronously
    runner = ContainerRunner(project_root, data_dir, image_name)
    container = runner.run_async(cmd_list, session.session_id)
    
    if container:
        # Update session with container ID
        session.container_id = container.id
        session.status = "running"
        session_manager.save_session(session)
        
        click.echo(f"Container started in background: {container.short_id}")
        click.echo(f"\nTo check status: claude-container sessions status {name}")
        click.echo(f"To view logs: claude-container sessions logs {name}")
        click.echo(f"To stop: claude-container sessions stop {name}")
    else:
        session.status = "failed"
        session_manager.save_session(session)
        click.echo("Failed to start container", err=True)