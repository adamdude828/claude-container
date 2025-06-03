"""MCP command group."""

import click

from .list_servers import list_servers
from .add_server import add_server
from .remove_server import remove_server


@click.group()
def mcp():
    """Manage MCP (Model Context Protocol) servers."""
    pass


# Add subcommands
mcp.add_command(list_servers, name='list')
mcp.add_command(add_server, name='add')
mcp.add_command(remove_server, name='remove')