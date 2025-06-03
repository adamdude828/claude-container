"""Clean command for Claude Container."""

import click
import shutil
from pathlib import Path

from ...services.docker_service import DockerService
from ...services.exceptions import DockerServiceError, ImageNotFoundError
from ...core.constants import DATA_DIR_NAME, CONTAINER_PREFIX


@click.command()
@click.option('--containers', '-c', is_flag=True, help='Also clean up task containers')
@click.option('--force', '-f', is_flag=True, help='Force remove running containers')
def clean(containers, force):
    """Clean up container data, images, and optionally task containers"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    try:
        # Initialize Docker service
        docker_service = DockerService()
        
        # Clean up task containers if requested
        if containers:
            click.echo("Cleaning up task containers...")
            # Use the project-specific prefix pattern
            name_prefix = f"{CONTAINER_PREFIX}-task-{project_root.name}".lower()
            
            # List containers with claude-container label
            containers = docker_service.list_containers(
                all=True,
                labels={
                    "claude-container": "true",
                    "claude-container-project": project_root.name.lower()
                }
            )
            
            # Filter by name prefix if needed
            containers = [c for c in containers if c.name.startswith(name_prefix)]
            removed = 0
            
            for container in containers:
                try:
                    if container.status == 'running' and not force:
                        click.echo(f"Skipping running container: {container.name}")
                        continue
                    
                    if container.status == 'running':
                        container.stop()
                    
                    docker_service.remove_container(container)
                    click.echo(f"Removed container: {container.name}")
                    removed += 1
                except Exception as e:
                    click.echo(f"Failed to remove container {container.name}: {e}")
            if removed > 0:
                click.echo(f"Removed {removed} task container(s)")
            else:
                click.echo("No task containers found")
        
        # Clean up image and data directory
        if data_dir.exists():
            image_name = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
            
            if docker_service.image_exists(image_name):
                try:
                    docker_service.remove_image(image_name)
                    click.echo(f"Removed image: {image_name}")
                except ImageNotFoundError:
                    pass  # Image was already gone
                except Exception as e:
                    click.echo(f"Warning: Could not remove image {image_name}: {e}")
            
            # Remove data directory
            shutil.rmtree(data_dir)
            click.echo("Cleaned up container resources")
        else:
            click.echo("No container data found")
            
    except DockerServiceError as e:
        click.echo(f"Error: {e}", err=True)
        return
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        return