"""Build command for Claude Container."""

import click
from pathlib import Path

from ...core.docker_client import DockerClient
from ...utils.path_finder import PathFinder
from ...utils.config_manager import ConfigManager
from ...models.container import ContainerConfig
from ...core.constants import DATA_DIR_NAME, CONTAINER_PREFIX


@click.command()
@click.option('--force-rebuild', is_flag=True, help='Force rebuild of container image')
@click.option('--tag', help='Tag for the container image')
@click.option('--claude-code-path', envvar='CLAUDE_CODE_PATH', help='Path to Claude Code executable')
def build(force_rebuild, tag, claude_code_path):
    """Build Docker container with project code included"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    data_dir.mkdir(exist_ok=True)
    
    try:
        # Initialize Docker client (checks connection)
        docker_client = DockerClient()
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        return
    
    # Generate tag if not provided
    if not tag:
        tag = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
    
    # Check if rebuild is needed
    if not force_rebuild and docker_client.image_exists(tag):
        click.echo(f"Image {tag} already exists. Use --force-rebuild to rebuild.")
        return
    
    # Remove existing image if force rebuild
    if force_rebuild and docker_client.image_exists(tag):
        click.echo(f"Removing existing image {tag}...")
        docker_client.remove_image(tag)
    
    click.echo(f"Building container for project: {project_root}")
    
    # Find Claude Code executable
    if not claude_code_path:
        path_finder = PathFinder()
        claude_code_path = path_finder.find_claude_code()
        if not claude_code_path:
            click.echo("Claude Code executable not found. Please specify --claude-code-path")
            return
    
    # Load or create container configuration
    config_manager = ConfigManager(data_dir)
    config = config_manager.get_container_config()
    if not config:
        config = ContainerConfig()
        config_manager.save_container_config(config)
    
    # Update config to include code
    config.include_code = True
    config.cached_image_tag = tag
    config_manager.save_container_config(config)
    
    # Build the image
    from ...core.dockerfile_generator import DockerfileGenerator
    from ...core.constants import DOCKERFILE_NAME
    
    generator = DockerfileGenerator(project_root)
    dockerfile_content = generator.generate_cached(include_code=True)
    
    temp_dockerfile = data_dir / DOCKERFILE_NAME
    try:
        # Write Dockerfile
        temp_dockerfile.write_text(dockerfile_content)
        
        # Build image
        docker_client.build_image(
            path=str(project_root),
            dockerfile=str(temp_dockerfile),
            tag=tag,
            rm=True,
            nocache=force_rebuild
        )
        
        click.echo(f"Container image built: {tag}")
        
        # Clean up Dockerfile
        if temp_dockerfile.exists():
            temp_dockerfile.unlink()
            
    except Exception as e:
        click.echo(f"Build failed: {e}")
        click.echo(f"Dockerfile saved at: {temp_dockerfile}")
        raise