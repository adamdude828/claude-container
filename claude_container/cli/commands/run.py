"""Run command for Claude Container."""

import click
from pathlib import Path

from ...core.docker_client import DockerClient
from ...core.container_runner import ContainerRunner
from ...core.constants import DATA_DIR_NAME, CONTAINER_PREFIX


@click.command(context_settings=dict(ignore_unknown_options=True))
@click.argument('command', nargs=-1, type=click.UNPROCESSED)
def run(command):
    """Run command in the container with Claude Code mounted"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    if not data_dir.exists():
        click.echo("No container found. Please run 'build' first.")
        return
    
    try:
        # Initialize Docker client (checks connection)
        docker_client = DockerClient()
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        return
    
    image_name = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
    
    click.echo("Running in container with Claude Code")
    
    # Run the command
    runner = ContainerRunner(project_root, data_dir, image_name)
    runner.run_command(list(command))