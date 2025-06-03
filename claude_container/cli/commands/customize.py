"""Customize command for Claude Container."""

import click
import subprocess
import sys
from datetime import datetime

from claude_container.cli.helpers import get_project_context, get_docker_client
from ...core.constants import CONTAINER_PREFIX, DEFAULT_WORKDIR
from ...utils.config_manager import ConfigManager
from ...models.container import ContainerConfig
from ...core.dockerfile_generator import DockerfileGenerator
from ...core.constants import DOCKERFILE_NAME


@click.command()
@click.option('--base-image', help='Base image to customize (defaults to current project image)')
@click.option('--tag', help='Tag for the customized image (defaults to project name)')
@click.option('--no-commit', is_flag=True, help='Exit without committing changes')
def customize(base_image, tag, no_commit):
    """Customize the container environment interactively.
    
    This command allows you to:
    - Enter the container with a shell
    - Install packages, dependencies, tools
    - Configure the environment
    - Exit and automatically save changes as a new image
    
    Perfect for non-Node.js projects or custom setups.
    """
    project_root, data_dir = get_project_context()
    data_dir.mkdir(exist_ok=True)
    
    # Initialize Docker client
    docker_client = get_docker_client()
    
    # Determine base image
    if not base_image:
        base_image = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
        
        # Check if base image exists, if not build it first
        if not docker_client.image_exists(base_image):
            click.echo(f"Base image '{base_image}' not found.")
            click.echo("Building base image first...")
            
            # Build base image
            try:
                # Check git configuration
                git_user_email = subprocess.check_output(['git', 'config', '--get', 'user.email'], 
                                                        text=True, stderr=subprocess.DEVNULL).strip()
                git_user_name = subprocess.check_output(['git', 'config', '--get', 'user.name'], 
                                                       text=True, stderr=subprocess.DEVNULL).strip()
            except subprocess.CalledProcessError:
                click.echo("Error: Git user configuration not found.", err=True)
                click.echo("Please configure git with:", err=True)
                click.echo('  git config --global user.email "you@example.com"', err=True)
                click.echo('  git config --global user.name "Your Name"', err=True)
                sys.exit(1)
            
            # Generate and build Dockerfile
            generator = DockerfileGenerator(project_root)
            dockerfile_content = generator.generate_cached(include_code=True)
            
            temp_dockerfile = data_dir / DOCKERFILE_NAME
            temp_dockerfile.write_text(dockerfile_content)
            
            buildargs = {
                'GIT_USER_EMAIL': git_user_email,
                'GIT_USER_NAME': git_user_name
            }
            
            docker_client.build_image(
                path=str(project_root),
                dockerfile=str(temp_dockerfile),
                tag=base_image,
                rm=True,
                buildargs=buildargs
            )
            
            # Clean up
            if temp_dockerfile.exists():
                temp_dockerfile.unlink()
            
            click.echo(f"✅ Base image built: {base_image}")
    
    # Determine target tag
    if not tag:
        tag = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
    
    # Create container name
    container_name = f"claude-customize-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    click.echo("\n" + "=" * 60)
    click.echo("🛠️  Claude Container Customization")
    click.echo("=" * 60)
    click.echo(f"\nBase image: {base_image}")
    click.echo(f"Target tag: {tag}")
    click.echo("\nYou are about to enter the container. You can:")
    click.echo("  - Install packages (apt-get, npm, pip, etc.)")
    click.echo("  - Configure the environment")
    click.echo("  - Set up tools and dependencies")
    click.echo("\nWhen done, type 'exit' to save your changes.")
    if no_commit:
        click.echo("\n⚠️  --no-commit specified: Changes will NOT be saved!")
    click.echo("\n" + "-" * 60)
    
    # Get volume mounts from ContainerRunner
    from ...core.container_runner import ContainerRunner
    container_runner = ContainerRunner(project_root, data_dir, base_image)
    volumes = container_runner._get_volumes()
    
    # Build docker run command
    docker_cmd = [
        'docker', 'run',
        '--name', container_name,
        '-it',
        '-w', DEFAULT_WORKDIR,
    ]
    
    # Add environment variables
    env = container_runner._get_container_environment()
    for key, value in env.items():
        docker_cmd.extend(['-e', f'{key}={value}'])
    
    # Add volume mounts
    for host_path, mount_info in volumes.items():
        bind_path = mount_info['bind']
        mode = mount_info.get('mode', 'rw')
        docker_cmd.extend(['-v', f'{host_path}:{bind_path}:{mode}'])
    
    # Add image
    docker_cmd.append(base_image)
    docker_cmd.append('/bin/bash')
    
    # Run interactive container
    click.echo("\n🚀 Starting container...\n")
    result = subprocess.run(docker_cmd)
    
    # After user exits, handle the container
    if result.returncode == 0 and not no_commit:
        click.echo("\n" + "-" * 60)
        click.echo("📦 Saving container changes...")
        
        try:
            # Get container object
            container = docker_client.client.containers.get(container_name)
            
            # Commit the container to create new image
            click.echo(f"Creating image: {tag}")
            container.commit(
                repository=tag,
                message=f"Customized environment for {project_root.name}",
                author="claude-container"
            )
            
            # Update configuration
            config_manager = ConfigManager(data_dir)
            config = config_manager.get_container_config()
            if not config:
                config = ContainerConfig()
            config.cached_image_tag = tag
            config.customized = True
            config.customized_at = datetime.now().isoformat()
            config_manager.save_container_config(config)
            
            click.echo(f"✅ Image saved as: {tag}")
            click.echo("\nYou can now use 'claude-container run' with your customized image!")
            
        except Exception as e:
            click.echo(f"\n❌ Error saving container: {e}", err=True)
        finally:
            # Clean up container
            try:
                container = docker_client.client.containers.get(container_name)
                container.remove(force=True)
                click.echo("🧹 Container cleaned up")
            except Exception:
                pass
    
    elif no_commit:
        # Just clean up without committing
        try:
            container = docker_client.client.containers.get(container_name)
            container.remove(force=True)
            click.echo("\n🧹 Container removed (--no-commit specified)")
        except Exception:
            pass
    
    else:
        click.echo("\n⚠️  Container exited with non-zero status. Changes not saved.")
        # Clean up container
        try:
            container = docker_client.client.containers.get(container_name)
            container.remove(force=True)
        except Exception:
            pass