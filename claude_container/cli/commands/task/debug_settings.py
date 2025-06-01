"""Debug settings task command."""

import sys
from pathlib import Path

import click

from ....core.constants import CONTAINER_PREFIX, DATA_DIR_NAME, DEFAULT_WORKDIR, LIBERAL_SETTINGS_JSON
from ....core.container_runner import ContainerRunner


@click.command()
def debug_settings():
    """Debug command to verify settings.local.json setup"""
    # Get project info
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME

    if not data_dir.exists():
        click.echo("No container found. Please run 'claude-container build' first.", err=True)
        sys.exit(1)

    image_name = f"{CONTAINER_PREFIX}-{project_root.name}".lower()

    try:
        container_runner = ContainerRunner(project_root, data_dir, image_name)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Check if image exists
    if not container_runner.docker_service.image_exists(image_name):
        click.echo(f"Container image '{image_name}' not found.", err=True)
        click.echo("Please run 'claude-container build' first.")
        sys.exit(1)

    container = None
    try:
        click.echo("Creating temporary container for debug...")
        container = container_runner.create_persistent_container("debug")

        # Create .claude directory
        click.echo("\n1. Creating .claude directory in workspace...")
        mkdir_result = container.exec_run(f"mkdir -p {DEFAULT_WORKDIR}/.claude")
        click.echo(f"   Result: {mkdir_result.exit_code} - {mkdir_result.output.decode()}")

        # Write settings file
        click.echo("\n2. Writing settings.local.json...")
        write_cmd = f"echo '{LIBERAL_SETTINGS_JSON}' > {DEFAULT_WORKDIR}/.claude/settings.local.json"
        write_result = container.exec_run(["sh", "-c", write_cmd])
        click.echo(f"   Result: {write_result.exit_code} - {write_result.output.decode()}")

        # Check if file was created
        click.echo("\n3. Checking if file exists...")
        check_result = container.exec_run(f"ls -la {DEFAULT_WORKDIR}/.claude/")
        click.echo(f"   Result: {check_result.exit_code}")
        click.echo(f"   Output:\n{check_result.output.decode()}")

        # Read file contents
        click.echo("\n4. Reading file contents...")
        read_result = container.exec_run(f"cat {DEFAULT_WORKDIR}/.claude/settings.local.json")
        click.echo(f"   Result: {read_result.exit_code}")
        click.echo(f"   Contents:\n{read_result.output.decode()}")

        # Check Claude's home directory
        click.echo("\n5. Checking Claude's home directory...")
        home_result = container.exec_run("ls -la /home/node/.claude/")
        click.echo(f"   Result: {home_result.exit_code}")
        click.echo(f"   Output:\n{home_result.output.decode()}")

        click.echo("\nDebug complete!")

    except Exception as e:
        click.echo(f"Error during debug: {e}", err=True)
        sys.exit(1)
    finally:
        if container:
            try:
                container.stop()
                container.remove()
                click.echo("Cleaned up debug container.")
            except Exception:
                pass
