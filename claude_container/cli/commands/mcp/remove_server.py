"""Remove MCP server command."""

from pathlib import Path

import click
from rich.console import Console
from rich.prompt import Confirm

from ....utils import MCPManager


@click.command()
@click.argument('name')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def remove_server(ctx, name: str, yes: bool):
    """Remove an MCP server configuration."""
    console = Console()
    project_root = Path.cwd()
    
    try:
        manager = MCPManager(project_root)
        
        # Check if server exists
        if not manager.get_server(name):
            console.print(f"[yellow]MCP server '{name}' not found[/yellow]")
            return
        
        # Confirm removal
        if not yes:
            if not Confirm.ask(f"Remove MCP server '{name}'?"):
                console.print("[yellow]Cancelled[/yellow]")
                return
        
        # Remove server
        if manager.remove_server(name):
            console.print(f"[green]Removed MCP server '{name}'[/green]")
        else:
            console.print(f"[red]Failed to remove MCP server '{name}'[/red]")
            ctx.exit(1)
        
    except Exception as e:
        console.print(f"[red]Error removing MCP server: {e}[/red]")
        ctx.exit(1)