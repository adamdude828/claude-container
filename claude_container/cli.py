import click
import os
from pathlib import Path
from .docker_manager import DockerManager


@click.group()
def cli():
    """Claude Container - Run Claude Code in isolated Docker environments"""
    pass


@cli.command()
@click.option('--dockerfile', help='Path to custom Dockerfile')
@click.option('--force-rebuild', is_flag=True, help='Force rebuild of container image')
@click.option('--claude-code-path', envvar='CLAUDE_CODE_PATH', help='Path to Claude Code executable')
def build(dockerfile, force_rebuild, claude_code_path):
    """Build Docker container for the current project"""
    project_root = Path.cwd()
    data_dir = project_root / '.claude-container'
    data_dir.mkdir(exist_ok=True)
    
    try:
        docker_manager = DockerManager(project_root, data_dir)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        return
    
    click.echo(f"Building container for project: {project_root}")
    
    # Find Claude Code executable
    if not claude_code_path:
        claude_code_path = docker_manager.find_claude_code()
        if not claude_code_path:
            click.echo("Claude Code executable not found. Please specify --claude-code-path")
            return
    
    # Check if there's an existing Dockerfile to reference
    existing_dockerfile = None
    if not dockerfile:
        default_dockerfile = project_root / 'Dockerfile'
        if default_dockerfile.exists():
            existing_dockerfile = str(default_dockerfile)
            click.echo(f"Found existing Dockerfile - will enhance it with Claude Code")
    elif dockerfile and Path(dockerfile).exists():
        existing_dockerfile = dockerfile
        click.echo(f"Using {dockerfile} as reference")
    
    click.echo("Using Claude Code to analyze project and generate optimized Dockerfile...")
    click.echo("Claude Code will test the Docker build to ensure it works correctly.")
    image_name = docker_manager.build_with_claude(claude_code_path, force_rebuild, existing_dockerfile)
    
    click.echo(f"Container image built: {image_name}")


@cli.command()
@click.argument('command', nargs=-1)
def run(command):
    """Run command in the container with Claude Code mounted"""
    project_root = Path.cwd()
    data_dir = project_root / '.claude-container'
    
    if not data_dir.exists():
        click.echo("No container found. Please run 'build' first.")
        return
    
    try:
        docker_manager = DockerManager(project_root, data_dir)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        return
    
    click.echo("Running in container with Claude Code")
    docker_manager.run_container(command)


@cli.command()
@click.option('--continue', 'continue_session', help='Continue a specific session by ID')
def start(continue_session):
    """Start a new Claude Code task with a description prompt"""
    project_root = Path.cwd()
    data_dir = project_root / '.claude-container'
    
    if not data_dir.exists():
        click.echo("No container found. Please run 'build' first.")
        return
    
    try:
        docker_manager = DockerManager(project_root, data_dir)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        return
    
    
    # Check Git origin
    if not docker_manager.check_git_ssh_origin():
        click.echo("WARNING: Git repository origin is not using SSH. This may cause issues with GitHub operations.")
        if not click.confirm("Do you want to continue anyway?"):
            return
    
    # Check if gh config can be mounted
    gh_config_dir = Path.home() / '.config' / 'gh'
    if gh_config_dir.exists():
        click.echo("GitHub CLI config found and will be mounted.")
        click.echo("Note: If you get permission errors, add ~/.config to Docker Desktop's file sharing settings.")
    
    if continue_session:
        click.echo(f"Continuing session: {continue_session}")
        docker_manager.start_task(continue_session=continue_session)
    else:
        # Prompt for task description
        task_description = click.prompt("Please describe your task")
        click.echo(f"Starting new task: {task_description}")
        docker_manager.start_task(task_description)


@cli.command()
def sessions():
    """List all Claude Code sessions for this project"""
    project_root = Path.cwd()
    data_dir = project_root / '.claude-container'
    
    if not data_dir.exists():
        click.echo("No container data found")
        return
    
    try:
        docker_manager = DockerManager(project_root, data_dir)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        return
    sessions = docker_manager.list_sessions()
    
    if not sessions:
        click.echo("No sessions found")
        return
    
    click.echo("Sessions:")
    for session in sessions:
        status = "✓" if session.get('completed') else "⚡"
        click.echo(f"{status} {session['id']} - {session['task']} ({session['created_at']})")


@cli.command()
def clean():
    """Clean up container data and images"""
    project_root = Path.cwd()
    data_dir = project_root / '.claude-container'
    
    if data_dir.exists():
        try:
            docker_manager = DockerManager(project_root, data_dir)
        except RuntimeError as e:
            click.echo(f"Error: {e}", err=True)
            return
        docker_manager.cleanup()
        click.echo("Cleaned up container resources")
    else:
        click.echo("No container data found")


if __name__ == '__main__':
    cli()