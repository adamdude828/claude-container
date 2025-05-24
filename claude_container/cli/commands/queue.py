"""Queue command group for Claude Container."""

import click
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

from ...core.docker_client import DockerClient
from ...core.container_runner import ContainerRunner
from ...core.constants import DATA_DIR_NAME, CONTAINER_PREFIX
from ...utils.session_manager import SessionManager


@click.group()
def queue():
    """Manage async container command queue"""
    pass


@queue.command('command', context_settings=dict(ignore_unknown_options=True))
@click.argument('command', nargs=-1, type=click.UNPROCESSED, required=True)
@click.option('--name', help='Name for this async session')
def queue_command(command, name):
    """Run async CLI command in the container"""
    if not command:
        click.echo("Error: No command provided. Please specify a command to run.")
        click.echo("Usage: claude-container queue command [OPTIONS] COMMAND...")
        return
    
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
    
    # Don't modify the command - we'll run as root with proper permissions
    cmd_list = list(command)
    
    # Run the command asynchronously
    runner = ContainerRunner(project_root, data_dir, image_name)
    container = runner.run_async(cmd_list, session.session_id)
    
    if container:
        # Update session with container ID
        session.container_id = container.id
        session.status = "running"
        session_manager.save_session(session)
        
        click.echo(f"Container started in background: {container.short_id}")
        click.echo(f"\nTo check status: claude-container queue status {name}")
        click.echo(f"To view logs: claude-container queue logs {name}")
        click.echo(f"To stop: claude-container queue stop {name}")
    else:
        session.status = "failed"
        session_manager.save_session(session)
        click.echo("Failed to start container", err=True)


@queue.command('status')
@click.argument('session_name')
def queue_status(session_name):
    """Check status of an async session"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    if not data_dir.exists():
        click.echo("No container data found.")
        return
    
    session_manager = SessionManager(data_dir)
    session = session_manager.get_session(session_name)
    
    if not session:
        click.echo(f"Session '{session_name}' not found")
        return
    
    # Get container status if available
    container_status = "Unknown"
    if session.container_id:
        try:
            docker_client = DockerClient()
            container = docker_client.client.containers.get(session.container_id)
            container_status = container.status
            
            # Update session status based on container status
            if container.status == "exited" and session.status == "running":
                session.status = "completed"
                session_manager.save_session(session)
        except Exception:
            container_status = "Not found"
            # If container not found and session still marked as running, update it
            if session.status == "running":
                session.status = "completed"
                session_manager.save_session(session)
    
    # Display session information
    status_data = [
        ["Session Name", session.name],
        ["Session ID", session.session_id],
        ["Status", session.status],
        ["Container Status", container_status],
        ["Command", ' '.join(session.command)],
        ["Created At", session.created_at.strftime("%Y-%m-%d %H:%M:%S")],
    ]
    
    click.echo(tabulate(status_data, tablefmt="grid"))


@queue.command('logs')
@click.argument('session_name')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
def queue_logs(session_name, follow):
    """View logs from an async session"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    if not data_dir.exists():
        click.echo("No container data found.")
        return
    
    session_manager = SessionManager(data_dir)
    session = session_manager.get_session(session_name)
    
    if not session:
        click.echo(f"Session '{session_name}' not found")
        return
    
    if not session.container_id:
        click.echo("No container ID found for this session")
        return
    
    try:
        docker_client = DockerClient()
        container = docker_client.client.containers.get(session.container_id)
        
        if follow:
            # Stream logs
            for line in container.logs(stream=True, follow=True):
                click.echo(line.decode('utf-8'), nl=False)
        else:
            # Get all logs
            logs = container.logs().decode('utf-8')
            click.echo(logs)
    except Exception as e:
        click.echo(f"Error getting logs: {e}", err=True)


@queue.command('stop')
@click.argument('session_name')
def queue_stop(session_name):
    """Stop a running async session"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    if not data_dir.exists():
        click.echo("No container data found.")
        return
    
    session_manager = SessionManager(data_dir)
    session = session_manager.get_session(session_name)
    
    if not session:
        click.echo(f"Session '{session_name}' not found")
        return
    
    if not session.container_id:
        click.echo("No container ID found for this session")
        return
    
    try:
        docker_client = DockerClient()
        container = docker_client.client.containers.get(session.container_id)
        
        click.echo(f"Stopping container {container.short_id}...")
        container.stop()
        
        # Update session status
        session.status = "stopped"
        session_manager.save_session(session)
        
        click.echo("Container stopped successfully")
    except Exception as e:
        click.echo(f"Error stopping container: {e}", err=True)