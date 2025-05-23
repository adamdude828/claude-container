"""Clean command for Claude Container."""

import click
import shutil
from pathlib import Path

from ...core.docker_client import DockerClient
from ...core.constants import DATA_DIR_NAME, CONTAINER_PREFIX


@click.command()
def clean():
    """Clean up container data and images"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    if data_dir.exists():
        try:
            # Initialize Docker client and remove image
            docker_client = DockerClient()
            image_name = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
            
            if docker_client.image_exists(image_name):
                docker_client.remove_image(image_name)
            
            # Remove data directory
            shutil.rmtree(data_dir)
            click.echo("Cleaned up container resources")
        except RuntimeError as e:
            click.echo(f"Error: {e}", err=True)
            return
    else:
        click.echo("No container data found")