"""Add MCP server command."""

import json
from pathlib import Path

import click
from rich.console import Console

from ....utils import MCPManager


@click.command()
@click.argument('name')
@click.argument('config')
@click.pass_context
def add_server(ctx, name: str, config: str):
    """Add or update an MCP server configuration.
    
    NAME: Server name (e.g., 'context7', 'telemetry')
    CONFIG: JSON configuration string or @file.json
    
    Examples:
        # Add stdio server
        claude-container mcp add context7 '{"type": "stdio", "command": "npx", "args": ["-y", "@upstash/context7-mcp"]}'
        
        # Add http server
        claude-container mcp add telemetry '{"type": "http", "url": "https://mcp.example.com"}'
        
        # Load from file
        claude-container mcp add myserver @server-config.json
    """
    console = Console()
    project_root = Path.cwd()
    
    try:
        # Parse configuration
        if config.startswith('@'):
            # Load from file
            config_file = Path(config[1:])
            if not config_file.exists():
                console.print(f"[red]Configuration file not found: {config_file}[/red]")
                ctx.exit(1)
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        else:
            # Parse JSON string
            try:
                config_data = json.loads(config)
            except json.JSONDecodeError as e:
                console.print(f"[red]Invalid JSON configuration: {e}[/red]")
                ctx.exit(1)
        
        # Validate required fields
        if 'type' not in config_data:
            console.print("[red]Configuration must include 'type' field[/red]")
            ctx.exit(1)
        
        if config_data['type'] == 'stdio' and 'command' not in config_data:
            console.print("[red]Stdio servers must include 'command' field[/red]")
            ctx.exit(1)
        
        if config_data['type'] == 'http' and 'url' not in config_data:
            console.print("[red]HTTP servers must include 'url' field[/red]")
            ctx.exit(1)
        
        # Add server
        manager = MCPManager(project_root)
        existing = manager.get_server(name)
        manager.add_server(name, config_data)
        
        if existing:
            console.print(f"[green]Updated MCP server '{name}'[/green]")
        else:
            console.print(f"[green]Added MCP server '{name}'[/green]")
        
        # Show current configuration
        console.print(f"\nConfiguration: {json.dumps(config_data, indent=2)}")
        
    except Exception as e:
        console.print(f"[red]Error adding MCP server: {e}[/red]")
        ctx.exit(1)