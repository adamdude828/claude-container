"""List MCP servers command."""

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from ....utils import MCPManager


@click.command()
@click.pass_context
def list_servers(ctx):
    """List all registered MCP servers."""
    console = Console()
    project_root = Path.cwd()
    
    try:
        manager = MCPManager(project_root)
        registry = manager.load_registry()
        
        if not registry.mcpServers:
            console.print("[yellow]No MCP servers registered.[/yellow]")
            console.print("Use 'claude-container mcp add' to register servers.")
            return
        
        # Create table
        table = Table(title="Registered MCP Servers")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Type", style="green")
        table.add_column("Configuration", style="white")
        
        for name, config in registry.mcpServers.items():
            config_dict = config.model_dump(exclude_none=True, exclude={"extra"})
            config_dict.update(config.extra)
            
            # Format configuration based on type
            if config.type == "stdio":
                config_str = f"Command: {config.command}"
                if config.args:
                    config_str += f" {' '.join(config.args)}"
            elif config.type == "http":
                config_str = f"URL: {config.url}"
            else:
                config_str = json.dumps(config_dict, separators=(',', ':'))
            
            table.add_row(name, config.type, config_str)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error loading MCP registry: {e}[/red]")
        ctx.exit(1)