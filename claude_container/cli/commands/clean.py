"""Clean command for Claude Container."""

import click
import shutil
from pathlib import Path

from ...core.docker_client import DockerClient
from ...core.constants import DATA_DIR_NAME, CONTAINER_PREFIX


@click.command()
@click.option('--containers', '-c', is_flag=True, help='Also clean up task containers')
@click.option('--force', '-f', is_flag=True, help='Force remove running containers')
def clean(containers, force):
    """Clean up container data, images, and optionally task containers"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    try:
        # Initialize Docker client
        docker_client = DockerClient()
        
        # Clean up task containers if requested
        if containers:
            click.echo("Cleaning up task containers...")
            # Use the project-specific prefix pattern
            name_prefix = f"{CONTAINER_PREFIX}-task-{project_root.name}".lower()
            removed = docker_client.cleanup_task_containers(
                name_prefix=name_prefix,
                project_name=project_root.name,
                force=force
            )
            if removed > 0:
                click.echo(f"Removed {removed} task container(s)")
            else:
                click.echo("No task containers found")
        
        # Clean up image and data directory
        if data_dir.exists():
            image_name = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
            
            if docker_client.image_exists(image_name):
                docker_client.remove_image(image_name)
            
            # Remove data directory
            shutil.rmtree(data_dir)
            click.echo("Cleaned up container resources")
        else:
            click.echo("No container data found")
            
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        return