"""Main CLI entry point for Claude Container."""

import click

from .commands.build import build
from .commands.run import run
from .commands.clean import clean
from .commands.config import config
from .commands.login import login
from .commands.auth_check import auth_check
from .commands.accept_permissions import accept_permissions
from .commands.check_permissions import check_permissions
from .commands.task import task
<<<<<<< HEAD
from .commands.adapt import adapt
=======
from .commands.mcp import mcp
>>>>>>> master


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
cli.add_command(accept_permissions)
cli.add_command(check_permissions)
cli.add_command(task)
<<<<<<< HEAD
cli.add_command(adapt)
=======
cli.add_command(mcp)
>>>>>>> master


if __name__ == '__main__':
    cli()