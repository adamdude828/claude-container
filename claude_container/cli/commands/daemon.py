"""Daemon command for Claude Container."""

import click
import subprocess
import sys
import os
import signal
from pathlib import Path

from ...core.daemon_client import DaemonClient


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


