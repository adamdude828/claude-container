"""Logs task command."""

import subprocess
import sys
from pathlib import Path

import click

from ....core.constants import DATA_DIR_NAME
from ....core.task_storage import TaskStorageManager


@click.command()
@click.argument('task_id')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--feedback', is_flag=True, help='Show feedback history instead of execution logs')
@click.option('--log-type', '-t', help='Specify log type to view (output/commit/all)')
@click.option('--continuation', '-c', type=int, help='View logs from specific continuation number')
def logs(task_id, follow, feedback, log_type, continuation):
    """View task execution logs"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME

    if not data_dir.exists():
        click.echo("Error: No container configuration found.", err=True)
        sys.exit(1)

    storage_manager = TaskStorageManager(data_dir)

    # Get task (support short IDs)
    task_metadata = storage_manager.get_task(task_id)
    if not task_metadata:
        # Try to find by short ID
        all_tasks = storage_manager.list_tasks()
        matching_tasks = [t for t in all_tasks if t.id.startswith(task_id)]
        if len(matching_tasks) == 1:
            task_metadata = matching_tasks[0]
            task_id = task_metadata.id
        elif len(matching_tasks) > 1:
            click.echo(f"Error: Multiple tasks found starting with '{task_id}'", err=True)
            sys.exit(1)
        else:
            click.echo(f"Error: No task found with ID: {task_id}", err=True)
            sys.exit(1)

    # Show feedback history if requested
    if feedback:
        if not task_metadata.feedback_history:
            click.echo("No feedback history found for this task.")
            return

        click.echo(f"\n💬 Feedback History for Task {task_id[:8]}:")
        click.echo("=" * 80)

        for i, entry in enumerate(task_metadata.feedback_history, 1):
            click.echo(f"\n[{i}] {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')} ({entry.feedback_type})")
            click.echo("-" * 40)
            click.echo(entry.feedback)

            if entry.claude_response_summary:
                click.echo(f"\n📝 Claude's Response: {entry.claude_response_summary}")
        return

    # Show execution logs
    task_dir = data_dir / "tasks" / "tasks" / task_id
    logs_dir = task_dir / "logs"

    if not logs_dir.exists():
        click.echo(f"No logs found for task {task_id[:8]}")
        return

    # Find all log files
    log_files = sorted(logs_dir.glob("*.log"))

    if not log_files:
        click.echo(f"No log files found in {logs_dir}")
        return

    # Filter by continuation if specified
    if continuation is not None:
        if continuation == 0:
            # Initial task logs (no continuation suffix)
            log_files = [f for f in log_files if not f.name.endswith(f"_cont_{continuation}.log") and "cont_" not in f.name]
        else:
            # Specific continuation logs
            log_files = [f for f in log_files if f.name.endswith(f"_cont_{continuation}.log")]

        if not log_files:
            click.echo(f"No logs found for continuation {continuation}")
            return

    # Group logs by type
    output_logs = []
    commit_logs = []
    other_logs = []

    for log_file in log_files:
        if "claude_output" in log_file.name:
            output_logs.append(log_file)
        elif "claude_commit" in log_file.name:
            commit_logs.append(log_file)
        else:
            other_logs.append(log_file)

    # If there's only one log file, just display it
    if len(log_files) == 1:
        log_file = log_files[0]
        click.echo(f"\n📋 Execution Logs for Task {task_id[:8]}:")
        click.echo(f"   Log file: {log_file.name}")
        click.echo("=" * 80)
    else:
        # Show available logs
        click.echo(f"\n📋 Available Logs for Task {task_id[:8]}:")
        click.echo("=" * 80)

        if output_logs:
            click.echo("\n🤖 Claude Output Logs:")
            for log in output_logs:
                click.echo(f"   - {log.name}")

        if commit_logs:
            click.echo("\n💾 Commit Logs:")
            for log in commit_logs:
                click.echo(f"   - {log.name}")

        if other_logs:
            click.echo("\n📄 Other Logs:")
            for log in other_logs:
                click.echo(f"   - {log.name}")

        # Determine which log to show based on log_type option
        if log_type == 'all':
            # Show all logs concatenated
            click.echo("\n📖 Showing all logs in chronological order")
            click.echo("-" * 80)
            for log in log_files:
                click.echo(f"\n\n{'='*20} {log.name} {'='*20}")
                try:
                    with open(log) as f:
                        click.echo(f.read())
                except Exception as e:
                    click.echo(f"Error reading {log.name}: {e}")
            return
        elif log_type == 'commit':
            if commit_logs:
                log_file = commit_logs[-1]  # Latest commit log
            else:
                click.echo("No commit logs found")
                return
        elif log_type == 'output':
            if output_logs:
                log_file = output_logs[-1]  # Latest output log
            else:
                click.echo("No output logs found")
                return
        else:
            # Default: prioritize the most recent output log
            if output_logs:
                log_file = output_logs[-1]  # Latest output log
            else:
                log_file = log_files[-1]  # Just show the latest log

        click.echo(f"\n📖 Showing: {log_file.name}")
        click.echo("-" * 80)

    if follow:
        # Follow mode - tail the log file
        try:
            subprocess.run(['tail', '-f', str(log_file)], check=True)
        except KeyboardInterrupt:
            click.echo("\nStopped following logs.")
    else:
        # Just display the contents
        try:
            with open(log_file) as f:
                click.echo(f.read())
        except Exception as e:
            click.echo(f"Error reading log file: {e}", err=True)
