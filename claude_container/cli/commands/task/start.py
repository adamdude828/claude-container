"""Deprecated start task command."""

import click
from .create import create


@click.command(hidden=True)
def start():
    """(Deprecated) Use 'task create' instead"""
    click.echo("This command is deprecated. Please use 'claude-container task create' instead.")
    ctx = click.get_current_context()
    ctx.invoke(create)