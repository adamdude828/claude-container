"""Copy command for Claude Container."""

import click
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from claude_container.cli.helpers import get_project_context, get_docker_client
from ...core.constants import CONTAINER_PREFIX, DEFAULT_WORKDIR


@click.command()
@click.argument('source', type=click.Path(exists=True))
@click.argument('destination', required=False)
def copy(source, destination):
    """Copy files or directories into the container.
    
    Examples:
        claude-container copy ./src /workspace/src
        claude-container copy package.json /workspace/
        claude-container copy . /workspace/
    """
    project_root, data_dir = get_project_context()
    
    # Initialize Docker client
    docker_client = get_docker_client()
    
    # Determine the image tag
    image_tag = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
    if not docker_client.image_exists(image_tag):
        click.echo(f"Error: Container image '{image_tag}' not found. Run 'build' first.")
        sys.exit(1)
    
    # Determine destination path
    source_path = Path(source)
    if not destination:
        # Default destination is /workspace/filename
        destination = f"{DEFAULT_WORKDIR}/{source_path.name}"
    elif destination.endswith('/'):
        # If destination ends with /, append source filename
        destination = f"{destination}{source_path.name}"
    
    # Create container name
    container_name = f"claude-copy-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    click.echo("\n" + "=" * 60)
    click.echo("📦 Claude Container Copy")
    click.echo("=" * 60)
    click.echo(f"\nSource: {source}")
    click.echo(f"Destination: {destination}")
    click.echo(f"Container image: {image_tag}")
    click.echo("\n" + "-" * 60)
    
    try:
        # Start a container from the current image
        click.echo("\n🚀 Starting temporary container...")
        container = docker_client.client.containers.run(
            image_tag,
            command="sleep infinity",
            name=container_name,
            detach=True,
            remove=False
        )
        
        # Copy files into the container
        click.echo(f"📋 Copying {source} to {destination}...")
        
        # Use docker cp command for reliable copying
        cp_cmd = ['docker', 'cp', str(source_path.absolute()), f"{container_name}:{destination}"]
        result = subprocess.run(cp_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            click.echo(f"\n❌ Error copying files: {result.stderr}", err=True)
            raise Exception(f"Copy failed: {result.stderr}")
        
        # Set proper ownership for copied files
        click.echo("🔧 Setting file ownership...")
        chown_cmd = f"chown -R node:node {destination}"
        exec_result = container.exec_run(chown_cmd, user='root')
        
        if exec_result.exit_code != 0:
            click.echo(f"⚠️  Warning: Failed to change ownership: {exec_result.output.decode()}")
        
        # Commit the container back to the same image tag
        click.echo(f"\n💾 Updating container image...")
        container.commit(
            repository=image_tag,
            message=f"Added {source_path.name} to {destination}",
            author="claude-container"
        )
        
        click.echo(f"\n✅ Successfully updated container with copied files!")
        click.echo("\nThe files have been added to your project's container.")
        
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        # Clean up container
        try:
            container = docker_client.client.containers.get(container_name)
            container.stop()
            container.remove()
            click.echo("\n🧹 Cleaned up temporary container")
        except Exception:
            pass