"""Helper functions for parsing Claude's stream-json output format."""

import json
import click
from typing import Iterator, Tuple, List


def parse_claude_stream_json(output_stream: Iterator, echo_to_screen: bool = True) -> Tuple[List[str], List[dict]]:
    """
    Parse Claude's stream-json output format.
    
    Args:
        output_stream: Iterator yielding chunks of output from Claude
        echo_to_screen: Whether to echo output to screen (currently outputs raw JSON)
        
    Returns:
        Tuple of (raw_output_lines, parsed_json_messages)
    """
    raw_output = []
    json_messages = []
    buffer = ""
    
    for chunk in output_stream:
        # Handle different types of streaming output
        if isinstance(chunk, bytes):
            decoded_chunk = chunk.decode()
        elif isinstance(chunk, int):
            # Docker streaming sometimes yields individual bytes as integers
            decoded_chunk = chr(chunk)
        else:
            decoded_chunk = str(chunk)
        
        raw_output.append(decoded_chunk)
        buffer += decoded_chunk
        
        # Try to parse complete JSON objects from the buffer
        lines = buffer.split('\n')
        buffer = ""
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # If this is the last line and doesn't end with a newline, it might be incomplete
            if i == len(lines) - 1 and not decoded_chunk.endswith('\n'):
                buffer = line
                continue
            
            try:
                json_obj = json.loads(line)
                json_messages.append(json_obj)
                
                # Display formatted output
                if echo_to_screen:
                    _display_json_message(json_obj)
                    
            except json.JSONDecodeError:
                # Not valid JSON, skip
                pass
    
    # Handle any remaining buffer content
    if buffer.strip():
        try:
            json_obj = json.loads(buffer)
            json_messages.append(json_obj)
            if echo_to_screen:
                _display_json_message(json_obj)
        except json.JSONDecodeError:
            pass
    
    return raw_output, json_messages


def _display_json_message(json_obj: dict) -> None:
    """Display a parsed JSON message in a user-friendly format.
    
    Based on the Anthropic SDK Message structure from the stream-json output.
    """
    msg_type = json_obj.get("type", "")
    
    if msg_type == "system" and json_obj.get("subtype") == "init":
        # Initial system message - this one is useful to show
        click.echo("\n\n🚀 Claude session initialized\n")
        tools = json_obj.get("tools", [])
        mcp_servers = json_obj.get("mcp_servers", [])
        if tools:
            click.echo(f"   Tools: {len(tools)} available\n")
        if mcp_servers:
            active_servers = [s for s in mcp_servers if s.get("status") == "active"]
            if mcp_servers:
                click.echo(f"   MCP Servers: {len(active_servers)}/{len(mcp_servers)} active\n")
        click.echo("")  # Extra line break after init
        
    elif msg_type == "user":
        # User messages contain tool results - not very useful to display
        # Skip these to reduce noise
        pass
        
    elif msg_type == "assistant":
        # Assistant's response with nested message structure
        message = json_obj.get("message", {})
        content = message.get("content", [])
        
        # Add some spacing before assistant messages
        click.echo("\n")
        
        # Content is a list of content blocks
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    block_type = block.get("type", "")
                    if block_type == "text":
                        text = block.get("text", "")
                        if text:
                            click.echo(text, nl=False)
                    elif block_type == "tool_use":
                        # Show tool usage in a subtle way
                        tool_name = block.get("name", "unknown")
                        click.echo(f"\n\n[Using {tool_name}...]\n", nl=False)
        
        # Add spacing after assistant messages
        click.echo("\n")
            
    elif msg_type == "result":
        # Final result message with stats - this is useful
        subtype = json_obj.get("subtype", "")
        cost_usd = json_obj.get("cost_usd", 0)
        duration_ms = json_obj.get("duration_ms", 0)
        num_turns = json_obj.get("num_turns", 0)
        
        click.echo("\n\n\n📊 Session Summary:\n")
        click.echo(f"   Status: {subtype}\n")
        click.echo(f"   Turns: {num_turns}\n")
        click.echo(f"   Duration: {duration_ms/1000:.1f}s\n")
        click.echo(f"   Cost: ${cost_usd:.4f}\n")
        
        if subtype == "error_max_turns":
            click.echo("   ⚠️  Maximum turns reached\n")
        elif subtype == "success" and json_obj.get("result"):
            result_text = json_obj.get("result", "")
            if result_text:
                click.echo(f"   Result: {result_text[:100]}..." if len(result_text) > 100 else f"   Result: {result_text}")
                click.echo("")  # Extra line break after result