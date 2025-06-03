"""Search tasks command."""

import click
import sys
from pathlib import Path
from tabulate import tabulate

from ....core.constants import DATA_DIR_NAME
from ....core.task_storage import TaskStorageManager
from ....models.task import TaskStatus


@click.command()
@click.argument('query')
def search(query):
    """Search tasks by description"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    if not data_dir.exists():
        click.echo("Error: No container configuration found.", err=True)
        sys.exit(1)
    
    storage_manager = TaskStorageManager(data_dir)
    
    # Search for matching tasks
    matching_tasks = storage_manager.search_tasks(query)
    
    if not matching_tasks:
        click.echo(f"\nNo tasks found matching '{query}'")
        return
    
    click.echo(f"\n📋 Tasks matching '{query}':")
    
    # Use the same table formatting as list command
    table_data = []
    for task_item in matching_tasks:
        # Truncate description to first line, max 50 chars
        desc_line = task_item.description.split('\n')[0]
        if len(desc_line) > 50:
            desc_line = desc_line[:47] + "..."
        
        # Format status with color
        status_colors = {
            TaskStatus.CREATED: 'green',
            TaskStatus.CONTINUED: 'yellow',
            TaskStatus.FAILED: 'red'
        }
        status_display = click.style(
            task_item.status.value.upper(), 
            fg=status_colors.get(task_item.status, 'white')
        )
        
        # Format dates
        created = task_item.created_at.strftime('%Y-%m-%d %H:%M')
        
        # Format PR URL if exists
        pr_display = ""
        if task_item.pr_url:
            # Extract PR number from URL (e.g., https://github.com/owner/repo/pull/123)
            pr_parts = task_item.pr_url.split('/')
            if len(pr_parts) >= 2 and pr_parts[-2] == 'pull':
                pr_number = pr_parts[-1]
                pr_display = click.style(f"PR #{pr_number}", fg='cyan')
            else:
                pr_display = click.style("PR", fg='cyan')
        
        # Add continuation count to description if exists
        if task_item.continuation_count > 0:
            desc_line += click.style(f" (cont: {task_item.continuation_count})", fg='yellow')
        
        # Build row
        row = [
            task_item.id[:8],  # Short ID
            status_display,
            task_item.branch_name,
            desc_line,
            created,
            pr_display
        ]
        
        table_data.append(row)
    
    # Print table with proper alignment
    headers = ["ID", "STATUS", "BRANCH", "DESCRIPTION", "CREATED", "PR"]
    table_str = tabulate(
        table_data, 
        headers=headers, 
        tablefmt="simple",
        colalign=("left", "left", "left", "left", "right", "left")
    )
    click.echo(table_str)
    
    click.echo(f"\nFound {len(matching_tasks)} matching task(s)")