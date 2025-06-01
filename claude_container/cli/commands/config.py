"""Configuration management commands for Claude Container."""

import json
from pathlib import Path

import click

from ...core.constants import DATA_DIR_NAME
from ...models.container import ContainerConfig
from ...utils.config_manager import ConfigManager


@click.group()
def config():
    """Manage container configuration"""
    pass


@config.command()
@click.argument('key')
@click.argument('value')
def env(key, value):
    """Set environment variable for container"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    config_manager = ConfigManager(data_dir)

    config_manager.update_env_vars({key: value})
    click.echo(f"Set environment variable: {key}={value}")


@config.command()
@click.argument('name', type=click.Choice(['python', 'node', 'go', 'rust', 'ruby', 'java']))
@click.argument('version')
def runtime(name, version):
    """Set runtime version for container"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    config_manager = ConfigManager(data_dir)

    config_manager.add_runtime_version(name, version)
    click.echo(f"Set {name} version to {version}")


@config.command()
@click.argument('command')
def add_command(command):
    """Add custom command to run during container build"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    config_manager = ConfigManager(data_dir)

    config_manager.add_custom_command(command)
    click.echo(f"Added custom command: {command}")


@config.command()
def show():
    """Display current container configuration"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    config_manager = ConfigManager(data_dir)

    config = config_manager.get_container_config()
    if not config:
        click.echo("No container configuration found")
        return

    click.echo("Container Configuration:")
    click.echo(json.dumps(config.model_dump(), indent=2))


@config.command()
def reset():
    """Reset container configuration to defaults"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    config_manager = ConfigManager(data_dir)

    config = ContainerConfig()
    config_manager.save_container_config(config)
    click.echo("Container configuration reset to defaults")
