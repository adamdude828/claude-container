"""Task command group and sub-commands."""

import click

from .create import create
from .continue_task import continue_task
from .list_tasks import list
from .show import show
from .delete import delete
from .start import start
from .logs import logs
from .search import search
from .history import history
from .cleanup import cleanup
from .debug_settings import debug_settings

__all__ = [
    'task',
    'create',
    'continue_task',
    'list',
    'show',
    'delete',
    'start',
    'logs',
    'search',
    'history',
    'cleanup',
    'debug_settings',
]


@click.group()
def task():
    """Manage Claude tasks"""
    pass


# Register all sub-commands
task.add_command(create)
task.add_command(continue_task)
task.add_command(list)
task.add_command(show)
task.add_command(delete)
task.add_command(start)
task.add_command(logs)
task.add_command(search)
task.add_command(history)
task.add_command(cleanup)
task.add_command(debug_settings)