"""Delete task command."""

import click
import sys
from pathlib import Path

from ....core.constants import DATA_DIR_NAME
from ....core.task_storage import TaskStorageManager


@click.command()
@click.argument('task_id')
@click.confirmation_option(prompt='Are you sure you want to delete this task?')
def delete(task_id):
    """Delete a task and all associated data"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    if not data_dir.exists():
        click.echo("Error: No container configuration found.", err=True)
        sys.exit(1)
    
    storage_manager = TaskStorageManager(data_dir)
    
    # Get task to verify it exists
    task_metadata = storage_manager.get_task(task_id)
    if not task_metadata:
        # Try short ID
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
    
    # Delete the task
    storage_manager.delete_task(task_id)
    
    click.echo(f"✅ Task {task_id[:8]} deleted successfully")
    click.echo(f"   Branch: {task_metadata.branch_name}")
    click.echo(f"   Description: {task_metadata.description.split(chr(10))[0]}...")