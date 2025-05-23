"""Start command for Claude Container."""

import click
from pathlib import Path

from ...core.docker_client import DockerClient
from ...core.container_runner import ContainerRunner
from ...utils.path_finder import PathFinder
from ...core.constants import DATA_DIR_NAME, CONTAINER_PREFIX


@click.command()
@click.option('--continue', 'continue_session', help='Continue a specific session by ID')
def start(continue_session):
    """Start a new Claude Code task with a description prompt"""
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
    
    # Check Git origin
    path_finder = PathFinder()
    if not path_finder.check_git_ssh_origin(project_root):
        click.echo("WARNING: Git repository origin is not using SSH. This may cause issues with GitHub operations.")
        if not click.confirm("Do you want to continue anyway?"):
            return
    
    # Check if gh config can be mounted
    gh_config_dir = Path.home() / '.config' / 'gh'
    if gh_config_dir.exists():
        click.echo("GitHub CLI config found and will be mounted.")
        click.echo("Note: If you get permission errors, add ~/.config to Docker Desktop's file sharing settings.")
    
    image_name = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
    runner = ContainerRunner(project_root, data_dir, image_name)
    
    if continue_session:
        click.echo(f"Continuing session: {continue_session}")
        runner.start_task(continue_session=continue_session)
    else:
        # Prompt for task description
        task_description = click.prompt("Please describe your task")
        click.echo(f"Starting new task: {task_description}")
        runner.start_task(task_description)