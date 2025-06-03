"""Build command for Claude Container."""

import click
import subprocess

from claude_container.cli.helpers import get_project_context, get_docker_client
from ...utils.path_finder import PathFinder
from ...utils.config_manager import ConfigManager
from ...models.container import ContainerConfig
from ...core.constants import CONTAINER_PREFIX


@click.command()
@click.option('--force-rebuild', is_flag=True, help='Force rebuild of container image even if it exists')
@click.option('--no-cache', is_flag=True, help='Build without using Docker cache (rebuilds all layers)')
@click.option('--tag', help='Tag for the container image')
@click.option('--claude-code-path', envvar='CLAUDE_CODE_PATH', help='Path to Claude Code executable')
def build(force_rebuild, no_cache, tag, claude_code_path):
    """Build Docker container with project code included"""
    project_root, data_dir = get_project_context()
    data_dir.mkdir(exist_ok=True)
    
    # Initialize Docker client (checks connection)
    docker_client = get_docker_client()
    
    # Generate tag if not provided
    if not tag:
        tag = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
    
    # Check if rebuild is needed
    if not force_rebuild and docker_client.image_exists(tag):
        click.echo(f"Image {tag} already exists. Use --force-rebuild to rebuild.")
        return
    
    click.echo(f"Building container for project: {project_root}")
    
    # Check git configuration
    try:
        git_user_email = subprocess.check_output(['git', 'config', '--get', 'user.email'], 
                                                text=True, stderr=subprocess.DEVNULL).strip()
        git_user_name = subprocess.check_output(['git', 'config', '--get', 'user.name'], 
                                               text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        git_user_email = ""
        git_user_name = ""
    
    if not git_user_email or not git_user_name:
        click.echo("Error: Git user configuration not found.", err=True)
        click.echo("Please configure git with:", err=True)
        click.echo('  git config --global user.email "you@example.com"', err=True)
        click.echo('  git config --global user.name "Your Name"', err=True)
        return
    
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
    dockerignore_path = project_root / '.dockerignore'
    dockerignore_backup = project_root / '.dockerignore.claude-backup'
    dockerignore_moved = False
    
    try:
        # Temporarily move .dockerignore if it exists
        if dockerignore_path.exists():
            click.echo("📦 Found .dockerignore - temporarily moving it to ensure complete project copy...")
            dockerignore_path.rename(dockerignore_backup)
            dockerignore_moved = True
        
        # Write Dockerfile
        temp_dockerfile.write_text(dockerfile_content)
        
        # Handle force rebuild by removing existing image
        if force_rebuild and docker_client.image_exists(tag):
            click.echo("Removing existing image...")
            docker_client.remove_image(tag)
        
        # Show build status messages
        if force_rebuild and no_cache:
            click.echo("Force rebuild enabled - rebuilding without Docker cache...")
        elif force_rebuild:
            click.echo("Force rebuild enabled - rebuilding image...")
        elif no_cache:
            click.echo("Building without cache - all layers will be rebuilt...")
        
        # Build image with git config as build args
        buildargs = {
            'GIT_USER_EMAIL': git_user_email,
            'GIT_USER_NAME': git_user_name
        }
        
        docker_client.build_image(
            path=str(project_root),
            dockerfile=str(temp_dockerfile),
            tag=tag,
            rm=True,
            nocache=no_cache,
            buildargs=buildargs
        )
        
        click.echo(f"Container image built: {tag}")
        
        # Clean up Dockerfile
        if temp_dockerfile.exists():
            temp_dockerfile.unlink()
            
    except Exception as e:
        click.echo(f"Build failed: {e}")
        click.echo(f"Dockerfile saved at: {temp_dockerfile}")
        raise
    finally:
        # Always restore .dockerignore if we moved it
        if dockerignore_moved and dockerignore_backup.exists():
            try:
                dockerignore_backup.rename(dockerignore_path)
                click.echo("✅ Restored .dockerignore file")
            except Exception as e:
                click.echo(f"⚠️  Warning: Could not restore .dockerignore: {e}", err=True)
                click.echo(f"   Backup is at: {dockerignore_backup}", err=True)