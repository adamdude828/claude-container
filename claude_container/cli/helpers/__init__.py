"""CLI Helper Functions for Claude Container.

This module provides reusable helper functions for CLI commands to reduce
code duplication and standardize behavior across all commands.

The helpers provide:
- Authentication and authorization checks
- Project context and configuration management
- Task ID resolution with short ID support
- Consistent table formatting for output
- Container lifecycle management
- Editor integration for user input
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, List, Optional, Tuple

import click
from tabulate import tabulate

from claude_container.core.constants import CONTAINER_PREFIX, DATA_DIR_NAME
from claude_container.core.container_runner import ContainerRunner
from claude_container.core.docker_client import DockerClient
from claude_container.core.task_storage import TaskStorageManager
from claude_container.models.config import ContainerConfig
from claude_container.models.task import TaskMetadata, TaskStatus
from claude_container.utils.config_manager import ConfigManager


def ensure_authenticated() -> None:
    """Ensure Claude is authenticated, exit gracefully on failure.

    This wraps check_claude_auth and provides consistent error handling.
    """
    from claude_container.cli.commands.auth_check import check_claude_auth

    if not check_claude_auth():
        sys.exit(1)


def get_project_context() -> tuple[Path, Path]:
    """Get project root and data directory with validation.

    Returns:
        Tuple of (project_root, data_dir)

    Note:
        Does not check if data_dir exists - callers should validate as needed.
    """
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    return project_root, data_dir


def ensure_container_built(data_dir: Path) -> None:
    """Ensure container has been built, exit with error if not.

    Args:
        data_dir: The data directory path to check
    """
    if not data_dir.exists():
        click.echo("No container found. Please run 'claude-container build' first.", err=True)
        sys.exit(1)


def get_storage_and_runner() -> tuple[TaskStorageManager, ContainerRunner]:
    """Initialize TaskStorageManager and ContainerRunner from context.

    Returns:
        Tuple of (storage_manager, runner)

    Note:
        This function handles all error cases and exits on failure.
    """
    project_root, data_dir = get_project_context()
    ensure_container_built(data_dir)

    storage_manager = TaskStorageManager(data_dir)

    image_name = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
    try:
        runner = ContainerRunner(project_root, data_dir, image_name)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Check if image exists
    if not runner.docker_service.image_exists(image_name):
        click.echo(f"Container image '{image_name}' not found.", err=True)
        click.echo("Please run 'claude-container build' first.")
        sys.exit(1)

    return storage_manager, runner


def get_docker_client() -> DockerClient:
    """Initialize Docker client with error handling.

    Returns:
        DockerClient instance

    Note:
        Exits with error message if Docker is not available.
    """
    try:
        return DockerClient()
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def get_config_manager() -> tuple[ConfigManager, ContainerConfig]:
    """Initialize ConfigManager and get/create container config.

    Returns:
        Tuple of (config_manager, config)
    """
    project_root, data_dir = get_project_context()
    ensure_container_built(data_dir)

    config_manager = ConfigManager(data_dir)
    config = config_manager.get_container_config()
    if not config:
        from datetime import datetime
        config = ContainerConfig(type="cached", generated_at=datetime.now().isoformat())
        config_manager.save_container_config(config)

    return config_manager, config


def resolve_task_id(storage_manager: TaskStorageManager, task_id: str) -> TaskMetadata:
    """Resolve a task ID with short ID support.

    Args:
        storage_manager: The task storage manager
        task_id: Full or partial task ID

    Returns:
        TaskMetadata for the resolved task

    Note:
        Exits with error if task not found or multiple matches.
    """
    task_metadata = storage_manager.get_task(task_id)
    if not task_metadata:
        # Try to find by short ID
        all_tasks = storage_manager.list_tasks()
        matching_tasks = [t for t in all_tasks if t.id.startswith(task_id)]

        if len(matching_tasks) == 1:
            task_metadata = matching_tasks[0]
        elif len(matching_tasks) > 1:
            click.echo(f"Error: Multiple tasks found starting with '{task_id}':", err=True)
            for task in matching_tasks:
                click.echo(f"  - {task.id}: {task.description.split()[0]}...", err=True)
            sys.exit(1)
        else:
            click.echo(f"Error: No task found with ID: {task_id}", err=True)
            sys.exit(1)

    return task_metadata


def format_pr_display(pr_url: Optional[str]) -> str:
    """Format PR URL for display.

    Args:
        pr_url: The PR URL or None

    Returns:
        Formatted PR display string
    """
    if not pr_url:
        return ""

    pr_parts = pr_url.split('/')
    if len(pr_parts) >= 2 and pr_parts[-2] == 'pull':
        pr_number = pr_parts[-1]
        return click.style(f"PR #{pr_number}", fg='cyan')
    else:
        return click.style("PR", fg='cyan')


def format_task_table(tasks: list[TaskMetadata],
                     headers: Optional[list[str]] = None,
                     max_desc_length: int = 50) -> str:
    """Format tasks as a table with consistent styling.

    Args:
        tasks: List of tasks to display
        headers: Optional custom headers (defaults to standard headers)
        max_desc_length: Maximum description length before truncation

    Returns:
        Formatted table string
    """
    if headers is None:
        headers = ["ID", "STATUS", "BRANCH", "DESCRIPTION", "CREATED", "PR"]

    status_colors = {
        TaskStatus.CREATED: 'green',
        TaskStatus.CONTINUED: 'yellow',
        TaskStatus.FAILED: 'red'
    }

    table_data = []
    for task_item in tasks:
        # Format description
        desc_line = task_item.description.split('\n')[0]
        if len(desc_line) > max_desc_length:
            desc_line = desc_line[:max_desc_length-3] + "..."

        # Add continuation count to description if exists
        if hasattr(task_item, 'continuation_count') and task_item.continuation_count > 0:
            desc_line += click.style(f" (cont: {task_item.continuation_count})", fg='yellow')

        # Format status with color
        status_display = click.style(
            task_item.status.value.upper(),
            fg=status_colors.get(task_item.status, 'white')
        )

        # Format PR
        pr_display = format_pr_display(task_item.pr_url)

        # Format dates
        created_str = task_item.created_at.strftime("%Y-%m-%d %H:%M")

        # Build row
        row = [
            task_item.id[:8],  # Short ID
            status_display,
            task_item.branch_name or "",
            desc_line,
            created_str,
            pr_display
        ]

        table_data.append(row)

    if table_data:
        return tabulate(table_data, headers=headers, tablefmt="simple",
                       colalign=("left", "left", "left", "left", "right", "left"))
    else:
        return tabulate(table_data, headers=headers, tablefmt="simple")


def print_table(headers: list[str], rows: list[list[Any]],
                tablefmt: str = "simple") -> None:
    """Print a table with project-wide defaults.

    Args:
        headers: Table headers
        rows: Table rows
        tablefmt: Table format (default: "simple")
    """
    table_str = tabulate(rows, headers=headers, tablefmt=tablefmt)
    click.echo(table_str)


def open_in_editor(template: str = "", suffix: str = ".md") -> str:
    """Open text in editor for user input.

    Args:
        template: Initial text to show in editor
        suffix: File suffix for temporary file

    Returns:
        The edited text

    Note:
        Returns empty string if user cancels or editor fails.
    """
    import os
    editor = os.environ.get('EDITOR', 'vim')

    try:
        with tempfile.NamedTemporaryFile(mode='w+', suffix=suffix, delete=False) as f:
            if template:
                f.write(template)
            f.flush()

            # Open editor
            result = subprocess.run([editor, f.name], check=False)
            if result.returncode != 0:
                click.echo("Editor exited with error.", err=True)
                return ""

            # Read result
            with open(f.name) as rf:
                content = rf.read()

            # Cleanup
            Path(f.name).unlink(missing_ok=True)

            return content.strip()

    except Exception as e:
        click.echo(f"Error opening editor: {e}", err=True)
        return ""


def cleanup_container(container: Any) -> None:
    """Clean up a Docker container with consistent error handling.

    Args:
        container: Docker container object to clean up
    """
    if container:
        try:
            click.echo("\n🧹 Cleaning up resources...")
            container.stop()
            container.remove()
            click.echo("✅ Container removed successfully")
        except Exception as e:
            click.echo(f"⚠️  Warning: Failed to remove container: {e}", err=True)


# Re-export commonly used functions for convenience
__all__ = [
    'ensure_authenticated',
    'get_project_context',
    'ensure_container_built',
    'get_storage_and_runner',
    'get_docker_client',
    'get_config_manager',
    'resolve_task_id',
    'format_pr_display',
    'format_task_table',
    'print_table',
    'open_in_editor',
    'cleanup_container',
]
