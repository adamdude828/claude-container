"""Sessions command for Claude Container."""

import click
from pathlib import Path
from datetime import datetime

from ...core.docker_client import DockerClient
from ...utils.session_manager import SessionManager
from ...core.constants import DATA_DIR_NAME


@click.group()
def sessions():
    """Manage async Claude Code sessions"""
    pass


@sessions.command()
def list():
    """List all Claude Code sessions for this project"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    if not data_dir.exists():
        click.echo("No container data found")
        return
    
    # List sessions
    session_manager = SessionManager(data_dir)
    session_list = session_manager.list_sessions()
    
    if not session_list:
        click.echo("No sessions found")
        return
    
    # Update session statuses based on actual container states and get container info
    docker_client = None
    container_info = {}
    
    for session in session_list:
        if session.container_id:
            try:
                if not docker_client:
                    docker_client = DockerClient()
                container = docker_client.client.containers.get(session.container_id)
                
                # Store container info
                container_info[session.session_id] = {
                    'name': container.name,
                    'status': container.status,
                    'exists': True
                }
                
                # If container has exited and session thinks it's running, update session status
                if session.status == "running" and container.status == "exited":
                    exit_code = container.attrs.get('State', {}).get('ExitCode', 1)
                    session.status = "completed" if exit_code == 0 else "failed"
                    session_manager.save_session(session)
            except:
                # Container not found
                container_info[session.session_id] = {
                    'name': session.container_id[:12] if session.container_id else 'N/A',
                    'status': 'not found',
                    'exists': False
                }
                
                # If session thinks it's running but container doesn't exist, mark as failed
                if session.status == "running":
                    session.status = "failed"
                    session_manager.save_session(session)
    
    click.echo("Sessions:")
    click.echo(f"{'  Status':<15} {'Name':<20} {'Container':<25} {'Live Status':<12} {'Command':<30} {'Created':<20}")
    click.echo("-" * 142)
    
    for session in session_list:
        status_icon = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌",
            "stopped": "⏹️"
        }.get(session.status, "❓")
        
        # Get container info for this session
        cont_info = container_info.get(session.session_id, {})
        container_name = cont_info.get('name', 'N/A')[:22] + "..." if len(cont_info.get('name', 'N/A')) > 25 else cont_info.get('name', 'N/A')
        live_status = cont_info.get('status', 'N/A') if cont_info.get('exists', False) else 'not found'
        
        cmd_str = ' '.join(session.command)[:27] + "..." if len(' '.join(session.command)) > 30 else ' '.join(session.command)
        created = session.created_at.strftime('%Y-%m-%d %H:%M:%S')
        
        click.echo(f"{status_icon} {session.status:<11} {session.name:<20} {container_name:<25} {live_status:<12} {cmd_str:<30} {created}")


@sessions.command()
@click.argument('session_name')
def status(session_name):
    """Check status of a specific session"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    if not data_dir.exists():
        click.echo("No container data found")
        return
    
    session_manager = SessionManager(data_dir)
    session = session_manager.get_session(session_name)
    
    if not session:
        click.echo(f"Session '{session_name}' not found")
        return
    
    # Update session status based on actual container state
    if session.container_id and session.status == "running":
        try:
            docker_client = DockerClient()
            container = docker_client.client.containers.get(session.container_id)
            
            # If container has exited, update session status
            if container.status == "exited":
                # Check exit code to determine if it was successful or failed
                exit_code = container.attrs.get('State', {}).get('ExitCode', 1)
                session.status = "completed" if exit_code == 0 else "failed"
                session_manager.save_session(session)
        except:
            # Container not found, mark as failed
            session.status = "failed"
            session_manager.save_session(session)
    
    click.echo(f"Session: {session.name}")
    click.echo(f"ID: {session.session_id}")
    click.echo(f"Status: {session.status}")
    click.echo(f"Command: {' '.join(session.command)}")
    click.echo(f"Created: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if session.container_id:
        try:
            docker_client = DockerClient()
            container = docker_client.client.containers.get(session.container_id)
            click.echo(f"Container: {container.short_id} ({container.status})")
        except:
            click.echo(f"Container: {session.container_id} (not found)")


@sessions.command()
@click.argument('session_name')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
def logs(session_name, follow):
    """View logs from a session"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    if not data_dir.exists():
        click.echo("No container data found")
        return
    
    session_manager = SessionManager(data_dir)
    session = session_manager.get_session(session_name)
    
    if not session:
        click.echo(f"Session '{session_name}' not found")
        return
    
    if not session.container_id:
        click.echo("No container associated with this session")
        return
    
    try:
        docker_client = DockerClient()
        container = docker_client.client.containers.get(session.container_id)
        
        if follow:
            # Stream logs
            for line in container.logs(stream=True, follow=True):
                click.echo(line.decode('utf-8'), nl=False)
        else:
            # Show all logs
            logs = container.logs()
            click.echo(logs.decode('utf-8'))
    except Exception as e:
        click.echo(f"Error getting logs: {e}", err=True)


@sessions.command()
@click.argument('session_name')
def stop(session_name):
    """Stop a running session"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    if not data_dir.exists():
        click.echo("No container data found")
        return
    
    session_manager = SessionManager(data_dir)
    session = session_manager.get_session(session_name)
    
    if not session:
        click.echo(f"Session '{session_name}' not found")
        return
    
    if session.status != "running":
        click.echo(f"Session is not running (status: {session.status})")
        return
    
    if not session.container_id:
        click.echo("No container associated with this session")
        return
    
    try:
        docker_client = DockerClient()
        container = docker_client.client.containers.get(session.container_id)
        container.stop()
        container.remove()
        
        session.status = "stopped"
        session_manager.save_session(session)
        
        click.echo(f"Session '{session_name}' stopped")
    except Exception as e:
        click.echo(f"Error stopping session: {e}", err=True)