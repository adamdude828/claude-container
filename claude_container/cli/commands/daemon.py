"""Daemon command for Claude Container."""

import click
import subprocess
import sys
import os
import signal
import time
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
    project_root = Path(__file__).parent.parent.parent.parent
    
    # Start daemon in background with proper daemonization
    # Redirect output to log files
    log_dir = Path.home() / ".claude-container"
    log_dir.mkdir(exist_ok=True)
    
    stdout_log = log_dir / "daemon.log"
    stderr_log = log_dir / "daemon.error.log"
    
    # Set PYTHONPATH to include project root
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root) + ':' + env.get('PYTHONPATH', '')
    
    # Use nohup to properly detach the daemon process
    with open(stdout_log, 'a') as out_file, open(stderr_log, 'a') as err_file:
        # On macOS/Unix, we need to properly detach the process
        if sys.platform != 'win32':
            # Use nohup to ensure process continues after parent exits
            process = subprocess.Popen(
                ['nohup', sys.executable, str(daemon_script)],
                stdout=out_file,
                stderr=err_file,
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                preexec_fn=os.setpgrp,  # Detach from parent process group
                cwd=str(project_root),
                env=env
            )
        else:
            # Windows doesn't have nohup
            process = subprocess.Popen(
                [sys.executable, str(daemon_script)],
                stdout=out_file,
                stderr=err_file,
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                cwd=str(project_root),
                env=env
            )
    
    # Save PID
    daemon_pid_file.write_text(str(process.pid))
    
    # Give daemon more time to start up and check multiple times
    for i in range(10):  # Check for up to 5 seconds
        time.sleep(0.5)
        try:
            os.kill(process.pid, 0)
            # Also try to connect to verify it's actually listening
            try:
                from ...core.daemon_client import DaemonClient
                client = DaemonClient()
                client.list_tasks()  # Test connection
                click.echo(f"✓ Daemon started successfully with PID {process.pid}")
                click.echo(f"\nLogs are being written to:")
                click.echo(f"  - Output: {stdout_log}")
                click.echo(f"  - Errors: {stderr_log}")
                click.echo("\nUseful commands:")
                click.echo("  claude-container daemon status    # Check daemon status")
                click.echo("  claude-container daemon stop      # Stop the daemon")
                click.echo(f"  tail -f {stdout_log}  # Watch logs")
                return
            except:
                # Connection failed, but process is running - keep trying
                if i == 9:  # Last attempt
                    click.echo(f"⚠ Daemon process started (PID {process.pid}) but not accepting connections yet")
                    click.echo(f"Check logs at {stderr_log}")
                continue
        except ProcessLookupError:
            click.echo(f"✗ Daemon failed to start. Check logs at {stderr_log}", err=True)
            if daemon_pid_file.exists():
                daemon_pid_file.unlink()
            sys.exit(1)


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
        
        # Show log file locations
        log_dir = Path.home() / ".claude-container"
        stdout_log = log_dir / "daemon.log"
        stderr_log = log_dir / "daemon.error.log"
        click.echo(f"\nLogs:")
        click.echo(f"  tail -f {stdout_log}")
        click.echo(f"  tail -f {stderr_log}")
            
    except ProcessLookupError:
        daemon_pid_file.unlink()
        click.echo("Daemon not running (process not found)")
    except Exception as e:
        click.echo(f"Error checking status: {e}", err=True)


