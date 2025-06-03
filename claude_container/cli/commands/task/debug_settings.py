"""Debug settings task command."""

import click


@click.command()
def debug_settings():
    """Debug command to verify settings setup (deprecated)"""
    click.echo("This command is deprecated.")
    click.echo("Claude Container now uses --dangerously-skip-permissions flag instead of settings.local.json")
    click.echo("\nTo accept permissions, run: claude-container accept-permissions")