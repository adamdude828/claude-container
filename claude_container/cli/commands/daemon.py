"""Daemon command for Claude Container."""

import click
import json
import subprocess
import sys
import os
import signal
from pathlib import Path

from ...core.docker_client import DockerClient
from ...core.daemon_client import DaemonClient
from ...core.constants import DATA_DIR_NAME, CONTAINER_PREFIX
from ...utils.session_manager import SessionManager


@click.group()
def daemon():
    """Manage the Claude task daemon"""
    pass


@daemon.command()
def start():
    """Start the task daemon on the host"""
    # Check if daemon is already running
    daemon_pid_file = Path.home() / ".claude-daemon.pid"
    
    if daemon_pid_file.exists():
        pid = int(daemon_pid_file.read_text().strip())
        try:
            # Check if process is running
            os.kill(pid, 0)
            click.echo(f"Daemon already running with PID {pid}")
            return
        except ProcessLookupError:
            # Process not running, clean up pid file
            daemon_pid_file.unlink()
    
    click.echo("Starting task daemon...")
    
    # Start daemon as a subprocess
    daemon_script = Path(__file__).parent.parent.parent / "core" / "task_daemon.py"
    
    # Start daemon in background
    process = subprocess.Popen(
        [sys.executable, str(daemon_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True
    )
    
    # Save PID
    daemon_pid_file.write_text(str(process.pid))
    
    click.echo(f"Daemon started with PID {process.pid}")
    click.echo("Use 'claude-container daemon status' to check status")
    click.echo("Use 'claude-container daemon stop' to stop the daemon")


@daemon.command()
def stop():
    """Stop the task daemon"""
    daemon_pid_file = Path.home() / ".claude-daemon.pid"
    
    if not daemon_pid_file.exists():
        click.echo("No daemon PID file found")
        return
    
    try:
        pid = int(daemon_pid_file.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        daemon_pid_file.unlink()
        click.echo(f"Daemon (PID {pid}) stopped")
    except ProcessLookupError:
        daemon_pid_file.unlink()
        click.echo("Daemon was not running")
    except Exception as e:
        click.echo(f"Error stopping daemon: {e}", err=True)


@daemon.command()
def status():
    """Check daemon status"""
    daemon_pid_file = Path.home() / ".claude-daemon.pid"
    
    if not daemon_pid_file.exists():
        click.echo("Daemon not running (no PID file)")
        return
    
    try:
        pid = int(daemon_pid_file.read_text().strip())
        os.kill(pid, 0)  # Check if process exists
        click.echo(f"Daemon running with PID {pid}")
        
        # Try to connect to daemon
        client = DaemonClient()
        response = client.list_tasks()
        
        if "error" in response:
            click.echo(f"Daemon communication error: {response['error']}")
        else:
            tasks = response.get("tasks", [])
            click.echo(f"Active tasks: {len(tasks)}")
            
    except ProcessLookupError:
        daemon_pid_file.unlink()
        click.echo("Daemon not running (process not found)")
    except Exception as e:
        click.echo(f"Error checking status: {e}", err=True)


@daemon.command()
@click.argument('command', nargs=-1, type=click.UNPROCESSED)
@click.option('--name', help='Name for this task')
def submit(command, name):
    """Submit a task to the daemon"""
    if not command:
        click.echo("No command provided")
        return
    
    # Get project info
    project_root = Path.cwd()
    
    client = DaemonClient()
    response = client.submit_task(list(command), str(project_root))
    
    if "error" in response:
        click.echo(f"Error: {response['error']}", err=True)
        return
    
    task_id = response.get("task_id")
    click.echo(f"Task submitted: {task_id}")
    click.echo(f"Status: {response.get('status')}")
    
    # Save task info
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    if data_dir.exists():
        session_manager = SessionManager(data_dir)
        session = session_manager.create_session(
            name or f"task_{task_id[:8]}", 
            list(command)
        )
        session.session_id = task_id
        session.status = "running"
        session_manager.save_session(session)


@daemon.command()
@click.argument('task_id')
def logs(task_id):
    """Get logs from a task"""
    client = DaemonClient()
    response = client.get_output(task_id)
    
    if "error" in response and isinstance(response.get("error"), str) and response["error"] and "task_id" not in response:
        # This is an API error (not task error output)
        click.echo(f"Error: {response['error']}", err=True)
        return
    
    output = response.get("output", "")
    error_output = response.get("error", "")
    
    if output:
        click.echo("=== OUTPUT ===")
        click.echo(output)
    
    if error_output:
        click.echo("\n=== ERROR ===")
        click.echo(error_output)
    
    if not output and not error_output:
        click.echo("No output yet")


@daemon.command()
def tasks():
    """List all tasks"""
    client = DaemonClient()
    response = client.list_tasks()
    
    if "error" in response:
        click.echo(f"Error: {response['error']}", err=True)
        return
    
    tasks = response.get("tasks", [])
    if not tasks:
        click.echo("No tasks")
        return
    
    click.echo(f"{'Task ID':<40} {'Status':<10} {'Command'}")
    click.echo("-" * 80)
    for task in tasks:
        task_id = task['task_id'][:8] + "..."
        status = task['status']
        command = task['command'][:40] + "..." if len(task['command']) > 40 else task['command']
        click.echo(f"{task_id:<40} {status:<10} {command}")