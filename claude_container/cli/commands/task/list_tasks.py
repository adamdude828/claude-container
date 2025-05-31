"""List tasks command."""

import click
from pathlib import Path
from tabulate import tabulate

from ....core.constants import CONTAINER_PREFIX, DATA_DIR_NAME
from ....core.docker_client import DockerClient
from ....core.task_storage import TaskStorageManager
from ....models.task import TaskStatus


@click.command()
@click.option('--status', type=click.Choice(['created', 'continued', 'failed']), 
              help='Filter by task status')
def list(status):
    """List all tasks (both stored and running containers)"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    # Show stored tasks
    if data_dir.exists():
        storage_manager = TaskStorageManager(data_dir)
        
        # Get tasks with optional status filter
        if status:
            tasks = storage_manager.list_tasks(TaskStatus(status))
        else:
            tasks = storage_manager.list_tasks()
        
        if tasks:
            click.echo(f"\n📋 Stored tasks for project '{project_root.name}':")
            
            # Prepare table data
            table_data = []
            for task_item in tasks:
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
        else:
            click.echo(f"\nNo stored tasks found for project '{project_root.name}'")
    
    # Also show running containers
    try:
        docker_client = DockerClient()
        
        # List containers for this project
        containers = docker_client.list_task_containers(
            name_prefix=f"{CONTAINER_PREFIX}-task",
            project_name=project_root.name
        )
        
        if containers:
            click.echo("\n🐳 Running task containers:")
            
            # Prepare container table data
            container_data = []
            for container in containers:
                status_val = container.status
                name = container.name
                created = container.attrs['Created'][:19]
                
                # Color code status
                if status_val == 'running':
                    status_display = click.style(status_val.upper(), fg='green')
                elif status_val == 'exited':
                    status_display = click.style(status_val.upper(), fg='yellow')
                else:
                    status_display = click.style(status_val.upper(), fg='red')
                
                container_data.append([name, status_display, created])
            
            # Print container table
            container_headers = ["CONTAINER NAME", "STATUS", "CREATED"]
            container_table = tabulate(
                container_data,
                headers=container_headers,
                tablefmt="simple"
            )
            click.echo(container_table)
                
    except RuntimeError as e:
        click.echo(f"\n⚠️  Warning: Could not list Docker containers: {e}", err=True)