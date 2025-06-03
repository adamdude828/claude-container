"""Continue task command."""

import json
import click
import sys
from pathlib import Path
from datetime import datetime

import questionary
from rich.console import Console

from ....core.container_runner import ContainerRunner
from ....core.constants import CONTAINER_PREFIX, DATA_DIR_NAME, DEFAULT_WORKDIR, MCP_CONFIG_PATH, CLAUDE_SKIP_PERMISSIONS_FLAG, CLAUDE_PERMISSIONS_ERROR
from ....core.task_storage import TaskStorageManager
from ....models.task import TaskStatus
from ....utils import MCPManager
from ...commands.auth_check import check_claude_auth
from ...util import get_feedback_from_editor


@click.command(name='continue')
@click.argument('task_identifier')
@click.option('--feedback', '-f', help='Inline feedback string')
@click.option('--feedback-file', type=click.Path(exists=True), help='File containing feedback')
@click.option('--mcp', help='Comma-separated list of MCP servers to use (overrides previous selection)')
def continue_task(task_identifier, feedback, feedback_file, mcp):
    """Continue an existing task with additional feedback"""
    # Verify Claude authentication
    if not check_claude_auth():
        sys.exit(1)
    
    # Initialize project configuration
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    if not data_dir.exists():
        click.echo("Error: No container found. Please run 'claude-container build' first.", err=True)
        sys.exit(1)
    
    # Initialize storage manager
    storage_manager = TaskStorageManager(data_dir)
    
    # Look up task (by ID or PR URL)
    if task_identifier.startswith("http"):
        task_metadata = storage_manager.lookup_task_by_pr(task_identifier)
        if not task_metadata:
            click.echo(f"Error: No task found for PR URL: {task_identifier}", err=True)
            sys.exit(1)
    else:
        # Try full ID first, then short ID
        task_metadata = storage_manager.get_task(task_identifier)
        if not task_metadata:
            # Try to find by short ID
            all_tasks = storage_manager.list_tasks()
            matching_tasks = [t for t in all_tasks if t.id.startswith(task_identifier)]
            if len(matching_tasks) == 1:
                task_metadata = matching_tasks[0]
            elif len(matching_tasks) > 1:
                click.echo(f"Error: Multiple tasks found starting with '{task_identifier}'", err=True)
                for t in matching_tasks:
                    click.echo(f"  - {t.id[:8]}: {t.description.split()[0]}...")
                sys.exit(1)
            else:
                click.echo(f"Error: No task found with ID: {task_identifier}", err=True)
                sys.exit(1)
    
    click.echo(f"\n📋 Continuing task {task_metadata.id[:8]}")
    click.echo(f"   Branch: {task_metadata.branch_name}")
    click.echo(f"   Description: {task_metadata.description.split(chr(10))[0]}...")
    if task_metadata.pr_url:
        click.echo(f"   PR: {task_metadata.pr_url}")
    click.echo(f"   Continuations: {task_metadata.continuation_count}")
    
    # Get feedback
    if feedback_file:
        with open(feedback_file, 'r') as f:
            feedback_content = f.read().strip()
        feedback_type = "file"
    elif feedback:
        feedback_content = feedback
        feedback_type = "inline"
    else:
        # Open editor for feedback
        click.echo("\nOpening editor for feedback...")
        feedback_content = get_feedback_from_editor()
        if not feedback_content:
            feedback_content = click.prompt("Feedback")
        feedback_type = "text"
    
    if not feedback_content or feedback_content.isspace():
        click.echo("\nError: Feedback cannot be empty.", err=True)
        sys.exit(1)
    
    # Store feedback
    storage_manager.add_feedback(task_metadata.id, feedback_content, feedback_type)
    
    image_name = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
    
    # Initialize container runner
    try:
        container_runner = ContainerRunner(project_root, data_dir, image_name)
    except RuntimeError as e:
        click.echo(f"Error initializing container: {e}", err=True)
        sys.exit(1)
    
    # Verify container image exists
    if not container_runner.docker_service.image_exists(image_name):
        click.echo(f"Error: Container image '{image_name}' not found.", err=True)
        sys.exit(1)
    
    container = None
    try:
        click.echo(f"\n🚀 Continuing task on branch '{task_metadata.branch_name}'...\n")
        
        # Create persistent container
        container = container_runner.create_persistent_container("task")
        storage_manager.update_task(task_metadata.id, container_id=container.id)
        
        # Check if permissions are accepted
        click.echo("🔍 Checking Claude permissions...")
        test_result = container.exec_run(
            ["claude", "-p", "echo test", CLAUDE_SKIP_PERMISSIONS_FLAG],
            workdir=DEFAULT_WORKDIR
        )
        
        if test_result.exit_code != 0 and CLAUDE_PERMISSIONS_ERROR in test_result.output.decode():
            click.echo("❌ Claude permissions have not been accepted yet.", err=True)
            click.echo("Please run 'claude-container accept-permissions' first.", err=True)
            
            # Cleanup container
            container.stop()
            container.remove()
            raise click.Abort()
        
        # Handle MCP server selection
        console = Console()
        mcp_manager = MCPManager(project_root)
        selected_servers = []
        
        try:
            all_servers = mcp_manager.list_servers()
            
            if mcp:
                # Use provided server list (overrides previous selection)
                requested = [s.strip() for s in mcp.split(',')]
                missing = mcp_manager.validate_server_names(requested)
                
                if missing:
                    console.print(f"[red]Error: Unknown MCP servers: {', '.join(missing)}[/red]")
                    console.print(f"Available servers: {', '.join(all_servers)}")
                    sys.exit(1)
                
                selected_servers = requested
                console.print(f"[green]Using MCP servers: {', '.join(selected_servers)}[/green]")
                
                # Update task metadata with new selection
                storage_manager.update_task(task_metadata.id, mcp_servers=selected_servers)
            
            elif task_metadata.mcp_servers:
                # Use servers from previous task run
                selected_servers = task_metadata.mcp_servers
                console.print(f"[green]Using MCP servers from previous run: {', '.join(selected_servers)}[/green]")
            
            elif all_servers and sys.stdin.isatty():
                # Interactive mode - show prompt
                console.print("\n[cyan]Select MCP servers to use for this task:[/cyan]")
                console.print("[dim]Previous selection: None[/dim]")
                
                # Add "All servers" option at the top
                choices = ["All servers"] + all_servers
                selected = questionary.checkbox(
                    "Available servers:",
                    choices=choices
                ).ask()
                
                if selected is None:
                    console.print("[yellow]No servers selected, continuing without MCP[/yellow]")
                elif "All servers" in selected:
                    selected_servers = all_servers
                    console.print(f"[green]Using all MCP servers: {', '.join(selected_servers)}[/green]")
                else:
                    selected_servers = selected
                    console.print(f"[green]Using MCP servers: {', '.join(selected_servers)}[/green]")
                
                # Update task metadata with new selection
                if selected_servers:
                    storage_manager.update_task(task_metadata.id, mcp_servers=selected_servers)
            
            else:
                # Non-interactive mode - use all available if no previous selection
                selected_servers = all_servers
                if selected_servers:
                    console.print(f"[green]Using all available MCP servers: {', '.join(selected_servers)}[/green]")
                    storage_manager.update_task(task_metadata.id, mcp_servers=selected_servers)
        
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to load MCP servers: {e}[/yellow]")
            # Continue without MCP servers
        
        # Write MCP configuration if servers are selected
        mcp_path = None
        if selected_servers:
            click.echo("🔧 Configuring MCP servers...")
            try:
                # Get filtered registry with only selected servers
                filtered_registry = mcp_manager.filter_registry(selected_servers)
                mcp_config = filtered_registry.to_mcp_json()
                mcp_config_str = json.dumps(mcp_config, indent=2)
                
                # Debug: Show MCP configuration
                click.echo("\n📋 MCP Configuration:")
                click.echo("-" * 60)
                click.echo(mcp_config_str)
                click.echo("-" * 60)
                
                # Write MCP configuration to container (outside workspace to avoid commits)
                mcp_path = f"/tmp/{MCP_CONFIG_PATH}"
                click.echo(f"\n📝 Writing MCP config to: {mcp_path}")
                container_runner.write_file(container, mcp_path, mcp_config_str)
                
                # Verify file was written
                verify_result = container.exec_run(
                    f"cat {mcp_path}",
                    workdir=DEFAULT_WORKDIR
                )
                if verify_result.exit_code == 0:
                    click.echo("✅ MCP config file verified in container")
                else:
                    click.echo(f"❌ Failed to verify MCP config file: {verify_result.output.decode()}")
                
                click.echo(f"✅ Configured {len(selected_servers)} MCP server(s)")
            except Exception as e:
                click.echo(f"⚠️  Warning: Failed to configure MCP servers: {e}", err=True)
                mcp_path = None
        
        # Fetch latest remote changes first
        click.echo("📥 Fetching latest remote changes...")
        fetch_result = container.exec_run(
            "git fetch --all",
            workdir=DEFAULT_WORKDIR
        )
        
        if fetch_result.exit_code != 0:
            click.echo(f"⚠️  Warning: Failed to fetch remote changes\n{fetch_result.output.decode()}", err=True)
        
        # Checkout branch
        click.echo(f"🌿 Checking out branch '{task_metadata.branch_name}'...")
        checkout_result = container.exec_run(
            f"git checkout {task_metadata.branch_name}",
            workdir=DEFAULT_WORKDIR
        )
        
        if checkout_result.exit_code != 0:
            click.echo(f"\n❌ Error: Failed to checkout branch\n{checkout_result.output.decode()}", err=True)
            raise Exception("Failed to checkout branch")
        
        # Pull latest changes
        click.echo("📥 Pulling latest changes...")
        pull_result = container.exec_run("git pull", workdir=DEFAULT_WORKDIR)
        
        if pull_result.exit_code != 0:
            click.echo(f"⚠️  Warning: Failed to pull latest changes\n{pull_result.output.decode()}", err=True)
        
        # Build context for Claude
        full_context = f"""You are continuing work on a task. Here is the original task description:

{task_metadata.description}

The task has been worked on {task_metadata.continuation_count - 1} time(s) before.

Here is the new feedback/requirements:

{feedback_content}

Please continue working on this task based on the feedback provided."""
        
        # Execute Claude with context
        click.echo("\n🤖 Running Claude with feedback...")
        click.echo("\n" + "-" * 60)
        click.echo("Claude is working on your task...")
        click.echo("-" * 60 + "\n")
        
        # Build Claude command with optional MCP config
        claude_cmd = ["claude", "--model=opus", "-p", full_context, CLAUDE_SKIP_PERMISSIONS_FLAG]
        if mcp_path:
            claude_cmd.extend(["--mcp-config", mcp_path])
        
        # Debug: Show the full command
        click.echo("\n🔍 Claude command:")
        click.echo(f"   {' '.join(claude_cmd[:6])}... [truncated]")
        if mcp_path:
            click.echo(f"   MCP config: {mcp_path}")
        
        claude_output = []
        claude_result = container.exec_run(
            claude_cmd,
            workdir=DEFAULT_WORKDIR,
            stream=True
        )
        
        for chunk in claude_result.output:
            decoded_chunk = chunk.decode()
            click.echo(decoded_chunk, nl=False)
            claude_output.append(decoded_chunk)
        
        # Save output
        storage_manager.save_task_log(
            task_metadata.id, 
            f"claude_output_cont_{task_metadata.continuation_count}", 
            ''.join(claude_output)
        )
        
        # Commit changes
        click.echo("\n\n💾 Having Claude commit the changes...")
        
        status_result = container.exec_run(
            "git status --porcelain",
            workdir=DEFAULT_WORKDIR
        )
        
        if not status_result.output.strip():
            click.echo("ℹ️  No changes to commit")
        else:
            commit_prompt = f"Please commit all the changes you made. Create a meaningful commit message that describes what was accomplished based on the feedback: {feedback_content}"
            
            click.echo("\n🤖 Asking Claude to commit the changes...")
            click.echo("-" * 60 + "\n")
            
            # Build Claude command with optional MCP config
            commit_cmd = ["claude", "--model=opus", "-p", commit_prompt, CLAUDE_SKIP_PERMISSIONS_FLAG]
            if mcp_path:
                commit_cmd.extend(["--mcp-config", mcp_path])
            
            commit_output = []
            commit_result = container.exec_run(
                commit_cmd,
                workdir=DEFAULT_WORKDIR,
                stream=True
            )
            
            for chunk in commit_result.output:
                decoded_chunk = chunk.decode()
                click.echo(decoded_chunk, nl=False)
                commit_output.append(decoded_chunk)
            
            # Save commit output
            storage_manager.save_task_log(
                task_metadata.id,
                f"claude_commit_cont_{task_metadata.continuation_count}",
                ''.join(commit_output)
            )
            
            # Check if a commit was actually made
            get_commit_msg = container.exec_run(
                "git log -1 --pretty=%B",
                workdir=DEFAULT_WORKDIR
            )
            
            if get_commit_msg.exit_code == 0:
                click.echo("\n\n✅ Changes committed successfully")
                
                # Get commit hash
                get_commit_hash = container.exec_run(
                    "git rev-parse HEAD",
                    workdir=DEFAULT_WORKDIR
                )
                if get_commit_hash.exit_code == 0:
                    commit_hash = get_commit_hash.output.decode().strip()
                    storage_manager.update_task(task_metadata.id, commit_hash=commit_hash)
                
                # Push changes
                click.echo(f"\n📤 Pushing changes to branch '{task_metadata.branch_name}'...")
                push_result = container.exec_run(
                    "git push",
                    workdir=DEFAULT_WORKDIR
                )
                
                if push_result.exit_code != 0:
                    click.echo(f"\n⚠️  Warning: Failed to push\n{push_result.output.decode()}", err=True)
                else:
                    click.echo("✅ Changes pushed successfully")
            else:
                click.echo("\n\n⚠️  Warning: No commit was made")
                click.echo("ℹ️  Claude may not have executed the commit command")
        
        # Update task status
        storage_manager.update_task(task_metadata.id, 
                                    completed_at=datetime.now(),
                                    container_id=None)
        
        click.echo("\n🎉 Task continuation completed!")
        click.echo(f"   Task ID: {task_metadata.id[:8]}")
        click.echo(f"   Branch: {task_metadata.branch_name}")
        if task_metadata.pr_url:
            click.echo(f"   PR: {task_metadata.pr_url}")
        
    except Exception as e:
        click.echo(f"\n❌ Error during task continuation: {e}", err=True)
        storage_manager.update_task(task_metadata.id,
                                    status=TaskStatus.FAILED,
                                    error_message=str(e),
                                    container_id=None)
        sys.exit(1)
        
    finally:
        if container:
            try:
                click.echo("\n🧹 Cleaning up resources...")
                container.stop()
                container.remove()
                click.echo("✅ Container removed successfully")
            except Exception as e:
                click.echo(f"⚠️  Warning: Failed to remove container: {e}", err=True)