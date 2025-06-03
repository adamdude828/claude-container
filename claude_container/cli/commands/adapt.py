"""Adapt existing Docker images or docker-compose services for Claude Code."""

import click
import sys
import os
import subprocess
import yaml
from typing import Optional, Dict, Any
from pathlib import Path

from claude_container.cli.helpers import get_project_context, get_docker_client
from claude_container.utils.config_manager import ConfigManager
from claude_container.core.container_runner import ContainerRunner
from claude_container.core.constants import CONTAINER_PREFIX


@click.command()
@click.option(
    '--image', '-i',
    help='Docker image to adapt for Claude Code'
)
@click.option(
    '--compose-file', '-f',
    type=click.Path(exists=True),
    help='Docker compose file to use'
)
@click.option(
    '--service', '-s',
    help='Service name from docker-compose file (required with --compose-file)'
)
@click.option(
    '--tag', '-t',
    help='Tag for the adapted image (default: original-tag-claude-adapted)'
)
@click.option(
    '--no-cache',
    is_flag=True,
    help='Build without cache when using docker-compose'
)
def adapt(image: Optional[str], compose_file: Optional[str], service: Optional[str], 
          tag: Optional[str], no_cache: bool) -> None:
    """Adapt an existing Docker image or docker-compose service for Claude Code.
    
    This command takes an existing Docker image or builds from a docker-compose file,
    then allows you to install Claude Code and make necessary modifications.
    
    Examples:
        claude-container adapt --image ubuntu:22.04
        claude-container adapt --compose-file docker-compose.yml --service web
    """
    # Get project context
    project_root, data_dir = get_project_context()
    data_dir.mkdir(exist_ok=True)
    
    # Initialize services
    config_manager = ConfigManager(data_dir)
    docker_client = get_docker_client()
    
    # Validate inputs
    if not image and not compose_file:
        click.echo("Error: You must provide either --image or --compose-file", err=True)
        sys.exit(1)
    
    if image and compose_file:
        click.echo("Error: Cannot use both --image and --compose-file", err=True)
        sys.exit(1)
    
    if compose_file and not service:
        click.echo("Error: --service is required when using --compose-file", err=True)
        sys.exit(1)
    
    try:
        # Step 1: Get or build the base image
        if compose_file:
            base_image = _build_from_compose(compose_file, service, no_cache)
        else:
            base_image = image
            # Pull image if it doesn't exist locally
            if not docker_client.image_exists(base_image):
                click.echo(f"Pulling image {base_image}...")
                docker_client.docker.images.pull(base_image)
        
        click.echo(f"\nUsing base image: {base_image}")
        
        # Step 2: Create adapted tag name
        if not tag:
            tag = f"{base_image.replace(':', '-')}-claude-adapted"
        
        # Step 3: Run container with Claude Code setup script
        click.echo("\nStarting container for Claude Code adaptation...")
        click.echo("You'll be logged into the container to install Claude Code.")
        click.echo("\nPlease follow the Claude Code setup instructions:")
        click.echo("https://docs.anthropic.com/en/docs/claude-code/getting-started")
        click.echo("\nKey steps:")
        click.echo("1. Install Node.js if not present (curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && apt-get install -y nodejs)")
        click.echo("2. Install Claude Code: npm install -g @anthropic-ai/claude-code")
        click.echo("3. Make any other necessary environment changes")
        click.echo("4. Type 'exit' when done to save changes\n")
        
        # Create a temporary container with necessary mounts
        volumes = {
            # Mount Claude auth files
            str(Path.home() / '.claude.json'): {
                'bind': '/home/node/.claude.json',
                'mode': 'rw'
            },
            str(Path.home() / '.claude'): {
                'bind': '/home/node/.claude',
                'mode': 'rw'
            },
            str(Path.home() / '.config/claude'): {
                'bind': '/home/node/.config/claude',
                'mode': 'rw'
            }
        }
        
        # Add SSH and Git configs as read-only
        ssh_dir = Path.home() / '.ssh'
        if ssh_dir.exists():
            volumes[str(ssh_dir)] = {'bind': '/root/.ssh', 'mode': 'ro'}
        
        gitconfig = Path.home() / '.gitconfig'
        if gitconfig.exists():
            volumes[str(gitconfig)] = {'bind': '/root/.gitconfig', 'mode': 'ro'}
        
        # Run interactive shell
        container_name = f"claude-adapt-{os.getpid()}"
        cmd = [
            'docker', 'run', '-it', '--rm',
            '--name', container_name,
            '--entrypoint', '/bin/bash'
        ]
        
        # Add volume mounts
        for host_path, mount_config in volumes.items():
            if Path(host_path).exists():
                cmd.extend(['-v', f"{host_path}:{mount_config['bind']}:{mount_config['mode']}"])
        
        cmd.append(base_image)
        
        # Store container name for commit
        config_manager.set_config('adapt_container_name', container_name)
        
        # Run the container
        result = subprocess.run(cmd)
        
        if result.returncode != 0:
            click.echo("Error: Failed to run container", err=True)
            sys.exit(1)
        
        # Step 4: Commit changes to new image
        click.echo(f"\nCommitting changes to {tag}...")
        
        # Note: Since we used --rm, we need a different approach
        # We'll need to run without --rm and commit after
        _commit_adapted_image(base_image, tag, volumes)
        
        click.echo(f"\nSuccessfully created adapted image: {tag}")
        click.echo("\nYou can now use this image with:")
        click.echo(f"  docker run -it {tag} claude-code")
        
        # Save the adapted image tag in config
        config_manager.set_config('adapted_image', tag)
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


def _build_from_compose(compose_file: str, service: str, no_cache: bool) -> str:
    """Build image from docker-compose file and return the image name."""
    click.echo(f"Building from docker-compose service '{service}'...")
    
    # Parse docker-compose file
    with open(compose_file, 'r') as f:
        compose_data = yaml.safe_load(f)
    
    if 'services' not in compose_data:
        raise ValueError("Invalid docker-compose file: no services found")
    
    if service not in compose_data['services']:
        raise ValueError(f"Service '{service}' not found in docker-compose file")
    
    # Build the service
    cmd = ['docker-compose', '-f', compose_file, 'build']
    if no_cache:
        cmd.append('--no-cache')
    cmd.append(service)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to build service: {result.stderr}")
    
    # Get the image name from docker-compose
    cmd = ['docker-compose', '-f', compose_file, 'config']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get compose config: {result.stderr}")
    
    config = yaml.safe_load(result.stdout)
    service_config = config['services'][service]
    
    # Try to get image name from config
    if 'image' in service_config:
        return service_config['image']
    else:
        # Generate image name based on project and service
        project_name = Path(compose_file).parent.name
        return f"{project_name}_{service}"


def _commit_adapted_image(base_image: str, tag: str, volumes: Dict[str, Any]) -> None:
    """Run container without --rm and commit changes."""
    container_name = f"claude-adapt-{os.getpid()}"
    
    # Run container without --rm
    cmd = [
        'docker', 'run', '-it',
        '--name', container_name,
        '--entrypoint', '/bin/bash'
    ]
    
    # Add volume mounts
    for host_path, mount_config in volumes.items():
        if Path(host_path).exists():
            cmd.extend(['-v', f"{host_path}:{mount_config['bind']}:{mount_config['mode']}"])
    
    cmd.append(base_image)
    
    # Run the container
    subprocess.run(cmd)
    
    # Commit the container
    commit_cmd = ['docker', 'commit', container_name, tag]
    result = subprocess.run(commit_cmd, capture_output=True, text=True)
    
    # Clean up container
    subprocess.run(['docker', 'rm', container_name], capture_output=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to commit container: {result.stderr}")