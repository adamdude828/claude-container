"""Cleanup task command."""

import click
import sys
from pathlib import Path
from tabulate import tabulate

from ....core.constants import CONTAINER_PREFIX
from ....services.docker_service import DockerService
from ....services.exceptions import DockerServiceError


@click.command()
@click.option('--force', '-f', is_flag=True, help='Force remove without confirmation')
def cleanup(force):
    """Remove all hanging task containers for this project"""
    project_root = Path.cwd()
    
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
        
        if not containers:
            click.echo(f"No task containers found for project '{project_root.name}'")
            return
        
        # Show containers that will be removed
        click.echo(f"\n🐳 Found {len(containers)} task container(s) for project '{project_root.name}':")
        
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
        
        # Confirm removal unless force flag is used
        if not force:
            if not click.confirm("\nDo you want to remove all these containers?"):
                click.echo("Cleanup cancelled.")
                return
        
        # Remove containers
        click.echo("\n🧹 Removing containers...")
        removed_count = 0
        failed_count = 0
        
        for container in containers:
            try:
                # Stop container if running
                if container.status == 'running':
                    click.echo(f"  Stopping {container.name}...")
                    container.stop()
                
                # Remove container
                click.echo(f"  Removing {container.name}...")
                docker_service.remove_container(container)
                removed_count += 1
            except Exception as e:
                click.echo(f"  ❌ Failed to remove {container.name}: {e}", err=True)
                failed_count += 1
        
        # Summary
        click.echo(f"\n✅ Successfully removed {removed_count} container(s)")
        if failed_count > 0:
            click.echo(f"⚠️  Failed to remove {failed_count} container(s)", err=True)
            
    except DockerServiceError as e:
        click.echo(f"Error: Could not access Docker: {e}", err=True)
        sys.exit(1)