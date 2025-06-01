"""List tasks command."""

import click
from claude_container.cli.helpers import get_project_context, format_task_table
from ....core.constants import CONTAINER_PREFIX
from ....services.docker_service import DockerService
from ....services.exceptions import DockerServiceError
from ....core.task_storage import TaskStorageManager
from ....models.task import TaskStatus


@click.command()
@click.option('--status', type=click.Choice(['created', 'continued', 'failed']), 
              help='Filter by task status')
def list(status):
    """List all tasks (both stored and running containers)"""
    project_root, data_dir = get_project_context()
    
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
            
            # Use helper to format and display task table
            table_str = format_task_table(tasks)
            click.echo(table_str)
        else:
            click.echo(f"\nNo stored tasks found for project '{project_root.name}'")
    
    # Also show running containers
    try:
        docker_service = DockerService()
        
        # List containers for this project
        containers = docker_service.list_containers(
            all=True,
            labels={
                "claude-container": "true",
                "claude-container-project": project_root.name.lower()
            }
        )
        
        # Filter by name prefix
        name_prefix = f"{CONTAINER_PREFIX}-task"
        containers = [c for c in containers if c.name.startswith(name_prefix)]
        
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
            from tabulate import tabulate
            container_headers = ["CONTAINER NAME", "STATUS", "CREATED"]
            container_table = tabulate(
                container_data,
                headers=container_headers,
                tablefmt="simple"
            )
            click.echo(container_table)
                
    except DockerServiceError as e:
        click.echo(f"\n⚠️  Warning: Could not list Docker containers: {e}", err=True)