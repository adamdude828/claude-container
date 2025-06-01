"""Main CLI entry point for Claude Container."""

import click

from .commands.auth_check import auth_check
from .commands.build import build
from .commands.clean import clean
from .commands.config import config
from .commands.login import login
from .commands.run import run
from .commands.task import task


@click.group()
def cli():
    """Claude Container - Run Claude Code in isolated Docker environments"""
    pass


# Register commands
cli.add_command(build)
cli.add_command(run)
cli.add_command(clean)
cli.add_command(config)
cli.add_command(login)
cli.add_command(auth_check)
cli.add_command(task)


if __name__ == '__main__':
    cli()
