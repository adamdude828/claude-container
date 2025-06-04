"""Create task command."""

import json
import click
import subprocess
import sys
from datetime import datetime

import questionary
from rich.console import Console

from claude_container.cli.helpers import (
    ensure_authenticated,
    get_storage_and_runner,
    cleanup_container
)
from ....core.constants import DEFAULT_WORKDIR, MCP_CONFIG_PATH, CLAUDE_SKIP_PERMISSIONS_FLAG, CLAUDE_PERMISSIONS_ERROR
from ....models.task import TaskStatus
from ....utils import MCPManager
from ....services.git_service import GitService, GitServiceError
from ...util import get_description_from_editor


def _get_exec_result(result):
    """Helper to handle both test mock and real docker exec result formats."""
    if hasattr(result, 'exit_code'):
        # Test mock format
        return result.exit_code, result.output
    else:
        # Real docker exec_run returns (exit_code, output)
        return result


def _is_streaming_result(result):
    """Check if the result is from a streaming command."""
    if hasattr(result, 'output'):
        # Mock result - check if output is an iterator
        return hasattr(result.output, '__iter__') and not isinstance(result.output, (bytes, str))
    else:
        # Real docker result - second element would be a generator
        return hasattr(result[1], '__iter__') and not isinstance(result[1], (bytes, str))


@click.command()
@click.option('--branch', '-b', help='Git branch name for the task')
@click.option('--file', '-f', 'description_file', type=click.Path(exists=True), 
              help='File containing task description')
@click.option('--mcp', help='Comma-separated list of MCP servers to use')
def create(branch, description_file, mcp):
    """Create a new task and run it to completion"""
    # Verify Claude authentication
    ensure_authenticated()
    
    # Initialize storage and runner
    storage_manager, container_runner = get_storage_and_runner()
    project_root = container_runner.project_root
    
    # Collect task parameters
    click.echo("\n" + "=" * 60)
    click.echo("Claude Container Task Setup")
    click.echo("=" * 60 + "\n")
    
    # Get branch name
    if not branch:
        branch = click.prompt("Branch name")
    
    # Get task description
    if description_file:
        with open(description_file, 'r') as f:
            task_description = f.read().strip()
    else:
        # Try to get description from editor first
        click.echo("\nOpening editor for task description...")
        task_description = get_description_from_editor()
        
        if task_description is None:
            # Fall back to simple prompt
            task_description = click.prompt("Task description")
    
    # Validate user inputs
    if not branch or branch.isspace():
        click.echo("\nError: Branch name cannot be empty.", err=True)
        sys.exit(1)
    
    if not task_description or task_description.isspace():
        click.echo("\nError: Task description cannot be empty.", err=True)
        sys.exit(1)
    
    # Handle MCP server selection
    console = Console()
    mcp_manager = MCPManager(project_root)
    selected_servers = []
    
    try:
        all_servers = mcp_manager.list_servers()
        
        if mcp:
            # Use provided server list
            requested = [s.strip() for s in mcp.split(',')]
            missing = mcp_manager.validate_server_names(requested)
            
            if missing:
                console.print(f"[red]Error: Unknown MCP servers: {', '.join(missing)}[/red]")
                console.print(f"Available servers: {', '.join(all_servers)}")
                sys.exit(1)
            
            selected_servers = requested
            console.print(f"[green]Using MCP servers: {', '.join(selected_servers)}[/green]")
        
        elif all_servers and sys.stdin.isatty():
            # Interactive mode - show prompt
            console.print("\n[cyan]Select MCP servers to use for this task:[/cyan]")
            
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
        
        else:
            # Non-interactive mode or no servers - use all available
            selected_servers = all_servers
            if selected_servers:
                console.print(f"[green]Using all available MCP servers: {', '.join(selected_servers)}[/green]")
    
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to load MCP servers: {e}[/yellow]")
        # Continue without MCP servers
    
    # Check if branch already exists locally or remotely before creating task
    try:
        # First fetch to ensure we have latest remote info
        click.echo("\n📥 Fetching latest remote information...")
        fetch_result = subprocess.run(
            ["git", "fetch", "--all"],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        if fetch_result.returncode != 0:
            click.echo("⚠️  Warning: Failed to fetch remote information", err=True)
        
        # Check for local branch
        local_branch_check = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
            capture_output=True,
            cwd=project_root
        )
        
        # Check for remote branch
        remote_branch_check = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/remotes/origin/{branch}"],
            capture_output=True,
            cwd=project_root
        )
        
        if local_branch_check.returncode == 0 or remote_branch_check.returncode == 0:
            click.echo(f"\nError: Branch '{branch}' already exists", err=True)
            if local_branch_check.returncode == 0:
                click.echo("  Found as local branch")
            if remote_branch_check.returncode == 0:
                click.echo("  Found on remote origin")
            click.echo("\nUse 'claude-container task continue' to work on an existing task")
            sys.exit(1)
    except subprocess.CalledProcessError:
        # This is fine - branch doesn't exist
        pass
    
    # Create task record
    task_metadata = storage_manager.create_task(task_description, branch)
    # Store selected MCP servers
    if selected_servers:
        task_metadata.mcp_servers = selected_servers
        storage_manager.update_task(task_metadata.id, mcp_servers=selected_servers)
    click.echo(f"\n✅ Created task {task_metadata.id[:8]} on branch '{branch}'")
    
    container = None
    try:
        click.echo(f"\n🚀 Starting task on branch '{branch}'...\n")
        
        # Update task status
        storage_manager.update_task(task_metadata.id, 
                                    started_at=datetime.now(),
                                    status=TaskStatus.CREATED)
        
        # Create persistent container for task execution
        container = container_runner.create_persistent_container("task", user="node")
        storage_manager.update_task(task_metadata.id, container_id=container.id)
        
        # Check if permissions are accepted
        click.echo("🔍 Checking Claude permissions...")
        test_result = container_runner.exec_in_container_as_user(
            container,
            ["claude", "-p", "echo test", CLAUDE_SKIP_PERMISSIONS_FLAG],
            user='node',
            workdir=DEFAULT_WORKDIR
        )
        
        exit_code, output = _get_exec_result(test_result)
        if exit_code != 0 and CLAUDE_PERMISSIONS_ERROR in output.decode():
            click.echo("❌ Claude permissions have not been accepted yet.", err=True)
            click.echo("Please run 'claude-container accept-permissions' first.", err=True)
            
            # Cleanup container
            container.stop()
            container.remove()
            storage_manager.delete_task(task_metadata.id)
            raise click.Abort()
        
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
                verify_result = container_runner.exec_in_container_as_user(
                    container,
                    f"cat {mcp_path}",
                    user='node',
                    workdir=DEFAULT_WORKDIR
                )
                exit_code, output = _get_exec_result(verify_result)
                if exit_code == 0:
                    click.echo("✅ MCP config file verified in container")
                else:
                    click.echo(f"❌ Failed to verify MCP config file: {output.decode()}")
                
                click.echo(f"✅ Configured {len(selected_servers)} MCP server(s)")
            except Exception as e:
                click.echo(f"⚠️  Warning: Failed to configure MCP servers: {e}", err=True)
                mcp_path = None
        
        # Step 1: Git branch setup
        click.echo(f"\n🌿 Setting up branch '{branch}'...")
        
        # Configure git to trust the workspace directory
        click.echo("🔧 Configuring git safe directory...")
        git_config_result = container_runner.exec_in_container_as_user(
            container,
            "git config --global --add safe.directory /workspace",
            user='node',
            workdir=DEFAULT_WORKDIR
        )
        exit_code, output = _get_exec_result(git_config_result)
        if exit_code != 0:
            click.echo(f"⚠️  Warning: Failed to configure git safe directory: {output.decode()}")
        
        # First, ensure we're on master and pull latest changes
        click.echo("📥 Switching to master and pulling latest changes...")
        
        # Check current branch first
        current_branch_result = container_runner.exec_in_container_as_user(
            container,
            "git branch --show-current",
            user='node',
            workdir=DEFAULT_WORKDIR
        )
        
        exit_code, output = _get_exec_result(current_branch_result)
        current_branch = output.decode().strip() if exit_code == 0 else ""
        
        # Only checkout master if we're not already on it
        if current_branch != "master":
            master_checkout_result = container_runner.exec_in_container_as_user(
                container,
                "git checkout master",
                user='node',
                workdir=DEFAULT_WORKDIR
            )
            
            exit_code, output = _get_exec_result(master_checkout_result)
            if exit_code != 0:
                click.echo(f"\n❌ Error: Failed to checkout master\n{output.decode()}", err=True)
                raise Exception("Failed to checkout master branch")
        else:
            click.echo("✅ Already on master branch")
        
        # Pull latest changes from master
        pull_result = container_runner.exec_in_container_as_user(
            container,
            "git pull origin master",
            user='node',
            workdir=DEFAULT_WORKDIR
        )
        
        exit_code, output = _get_exec_result(pull_result)
        if exit_code != 0:
            click.echo(f"\n❌ Error: Failed to pull latest changes\n{output.decode()}", err=True)
            raise Exception("Failed to pull latest changes from master")
        
        click.echo("✅ Successfully pulled latest changes from master")
        
        # Create new branch from updated master
        checkout_result = container_runner.exec_in_container_as_user(
            container,
            f"git checkout -b {branch}",
            user='node',
            workdir=DEFAULT_WORKDIR
        )
        
        exit_code, output = _get_exec_result(checkout_result)
        if exit_code != 0:
            click.echo(f"\n❌ Error: Failed to create branch\n{output.decode()}", err=True)
            raise Exception("Failed to create branch")
        
        # Step 2: Execute Claude task
        click.echo(f"\n🤖 Running Claude with task:\n   {task_description}")
        click.echo("\n" + "-" * 60)
        click.echo("Claude is working on your task...")
        click.echo("-" * 60 + "\n")
        
        # Build full output for logging
        claude_output = []
        
        # Build Claude command with optional MCP config
        claude_cmd = ["claude", "--model=opus", "-p", task_description, CLAUDE_SKIP_PERMISSIONS_FLAG]
        if mcp_path:
            claude_cmd.extend(["--mcp-config", mcp_path])
        
        # Debug: Show the full command
        click.echo("\n🔍 Claude command:")
        click.echo(f"   {' '.join(claude_cmd[:6])}... [truncated]")
        if mcp_path:
            click.echo(f"   MCP config: {mcp_path}")
        
        # Execute Claude with the task
        claude_result = container_runner.exec_in_container_as_user(
            container,
            claude_cmd,
            user='node',
            workdir=DEFAULT_WORKDIR,
            stream=True
        )
        
        # Stream Claude's output in real-time
        # For streaming results, we need to handle the output differently
        if hasattr(claude_result, 'output'):
            # Mock result format
            output_stream = claude_result.output
        else:
            # Real docker format - when stream=True, it returns a generator directly
            output_stream = claude_result
        
        for chunk in output_stream:
            # Handle different types of streaming output
            if isinstance(chunk, bytes):
                decoded_chunk = chunk.decode()
            elif isinstance(chunk, int):
                # Docker streaming sometimes yields individual bytes as integers
                decoded_chunk = chr(chunk)
            else:
                decoded_chunk = str(chunk)
            click.echo(decoded_chunk, nl=False)
            claude_output.append(decoded_chunk)
        
        # Save Claude output log
        storage_manager.save_task_log(task_metadata.id, "claude_output", ''.join(claude_output))
        
        # Step 3: Have Claude commit the changes
        click.echo("\n\n💾 Having Claude commit the changes...")
        
        # Check if there are changes to commit
        status_result = container_runner.exec_in_container_as_user(
            container,
            "git status --porcelain",
            user='node',
            workdir=DEFAULT_WORKDIR
        )
        
        exit_code, output = _get_exec_result(status_result)
        # Handle case where output might be an iterator (shouldn't happen for non-streaming commands)
        if hasattr(output, '__iter__') and not isinstance(output, (bytes, str)):
            # Consume the iterator and join the results
            output = b''.join(output)
        
        if not output or not output.strip():
            click.echo("ℹ️  No changes to commit")
            commit_message = None
        else:
            # Ask Claude to commit the changes
            commit_prompt = f"""Please commit all the changes you made. Review the changes with git diff and git status, then create a semantic commit message following the Conventional Commits specification.

Use one of these types: feat, fix, docs, style, refactor, test, chore, perf, build, ci
Format: <type>(<scope>): <description>

Examples:
- feat(auth): add OAuth2 login support
- fix(api): resolve null pointer in user service
- docs(readme): update installation instructions
- refactor(core): simplify error handling logic

Task context: {task_description}

Create a concise, semantic commit message that describes what was accomplished. Do NOT include any attribution, emojis, or Co-Authored-By lines."""
            
            click.echo("\n🤖 Asking Claude to commit the changes...")
            click.echo("-" * 60 + "\n")
            
            # Build Claude command with optional MCP config
            commit_cmd = ["claude", "--model=opus", "-p", commit_prompt, CLAUDE_SKIP_PERMISSIONS_FLAG]
            if mcp_path:
                commit_cmd.extend(["--mcp-config", mcp_path])
            
            commit_output = []
            commit_result = container_runner.exec_in_container_as_user(
                container,
                commit_cmd,
                user='node',
                workdir=DEFAULT_WORKDIR,
                stream=True
            )
            
            # Stream Claude's commit output
            # For streaming results, we need to handle the output differently
            if hasattr(commit_result, 'output'):
                # Mock result format
                output_stream = commit_result.output
            else:
                # Real docker format - when stream=True, it returns a generator directly
                output_stream = commit_result
            
            for chunk in output_stream:
                # Handle different types of streaming output
                if isinstance(chunk, bytes):
                    decoded_chunk = chunk.decode()
                elif isinstance(chunk, int):
                    # Docker streaming sometimes yields individual bytes as integers
                    decoded_chunk = chr(chunk)
                else:
                    decoded_chunk = str(chunk)
                click.echo(decoded_chunk, nl=False)
                commit_output.append(decoded_chunk)
            
            # Save commit output
            storage_manager.save_task_log(task_metadata.id, "claude_commit", ''.join(commit_output))
            
            # Extract commit message from the last commit
            get_commit_msg = container_runner.exec_in_container_as_user(
                container,
                "git log -1 --pretty=%B",
                user='node',
                workdir=DEFAULT_WORKDIR
            )
            
            exit_code, output = _get_exec_result(get_commit_msg)
            if exit_code == 0:
                commit_message = output.decode().strip()
                click.echo("\n\n✅ Changes committed successfully")
                
                # Get commit hash
                get_commit_hash = container_runner.exec_in_container_as_user(
                    container,
                    "git rev-parse HEAD",
                    user='node',
                    workdir=DEFAULT_WORKDIR
                )
                exit_code, output = _get_exec_result(get_commit_hash)
                if exit_code == 0:
                    commit_hash = output.decode().strip()
                    storage_manager.update_task(task_metadata.id, commit_hash=commit_hash)
            else:
                click.echo("\n\n⚠️  Warning: Could not retrieve commit message")
                commit_message = f"Task: {task_description}"
        
        # Push to remote repository only if there was a commit
        if commit_message:
            click.echo(f"\n📤 Pushing branch '{branch}' to remote...")
            push_result = container_runner.exec_in_container_as_user(
                container,
                f"git push -u origin {branch}",
                user='node',
                workdir=DEFAULT_WORKDIR
            )
            
            exit_code, output = _get_exec_result(push_result)
            if exit_code != 0:
                click.echo(f"\n❌ Error: Failed to push branch\n{output.decode()}", err=True)
                raise Exception("Failed to push branch")
            
            # Step 4: Create pull request
            click.echo("\n🔀 Creating pull request...")
            
            # Extract first line of commit message for PR title
            pr_title = commit_message.split('\n')[0]
            # Use full commit message in PR body
            pr_body = f"## 📋 Task Description\n\n{task_description}\n\n## 💬 Changes Made\n\n{commit_message}\n\n---\n\n*This PR was created automatically by claude-container task*"
            
            try:
                pr_result = subprocess.run(
                    [
                        "gh", "pr", "create",
                        "--title", pr_title,
                        "--body", pr_body,
                        "--head", branch,
                        "--draft"
                    ],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                click.echo("\n✅ Pull request created successfully!")
                click.echo(pr_result.stdout)
                
                # Extract PR URL from output
                pr_url = pr_result.stdout.strip()
                if pr_url.startswith("https://"):
                    storage_manager.update_task(task_metadata.id, pr_url=pr_url)
                
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr if e.stderr else str(e)
                click.echo(f"\n❌ Error: Failed to create PR\n{error_msg}", err=True)
                click.echo("\nℹ️  Make sure you have the GitHub CLI installed and authenticated")
        else:
            click.echo("\n⚠️  No changes were made, skipping PR creation")
        
        # Mark task as completed
        storage_manager.update_task(task_metadata.id, 
                                    completed_at=datetime.now(),
                                    container_id=None)
        
        click.echo("\n🎉 Task completed successfully!")
        click.echo(f"   Task ID: {task_metadata.id[:8]}")
        click.echo(f"   Branch: {branch}")
        if commit_message:
            click.echo("   Status: PR created and ready for review")
        else:
            click.echo("   Status: No changes were made")
        
    except Exception as e:
        click.echo(f"\n❌ Error during task execution: {e}", err=True)
        storage_manager.update_task(task_metadata.id,
                                    status=TaskStatus.FAILED,
                                    error_message=str(e),
                                    completed_at=datetime.now(),
                                    container_id=None)
        sys.exit(1)
        
    finally:
        # Step 5: Cleanup
        cleanup_container(container)