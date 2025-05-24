"""Main CLI entry point for Claude Container."""

import click

from .commands.build import build
from .commands.run import run
from .commands.run_async import run_async
from .commands.start import start
from .commands.sessions import sessions
from .commands.clean import clean
from .commands.config import config
from .commands.daemon import daemon


@click.group()
def cli():
    """Claude Container - Run Claude Code in isolated Docker environments"""
    pass


# Register commands
cli.add_command(build)
cli.add_command(run)
cli.add_command(run_async)
cli.add_command(start)
cli.add_command(sessions)
cli.add_command(clean)
cli.add_command(config)
cli.add_command(daemon)


if __name__ == '__main__':
    cli()