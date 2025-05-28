"""Task command for Claude Container."""

import click
import subprocess
import sys
from pathlib import Path

from ...core.daemon_client import DaemonClient
from ...core.docker_client import DockerClient
from ...core.constants import CONTAINER_PREFIX, DATA_DIR_NAME
from ..commands.auth_check import check_claude_auth


@click.group()
def task():
    """Manage Claude tasks"""
    pass


@task.command()
def start():
    """Start a new task with Claude authentication check"""
    # Check authentication first
    if not check_claude_auth():
        sys.exit(1)
    
    # Get project info
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    if not data_dir.exists():
        click.echo("No container found. Please run 'claude-container build' first.", err=True)
        sys.exit(1)
    
    try:
        docker_client = DockerClient()
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    
    image_name = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
    
    # Check if image exists
    if not docker_client.image_exists(image_name):
        click.echo(f"Container image '{image_name}' not found.", err=True)
        click.echo("Please run 'claude-container build' first.")
        sys.exit(1)
    
    # Prompt for branch name and task description
    branch_name = click.prompt("Enter the branch name for this task")
    task_description = click.prompt("Enter the task description")
    
    # Validate inputs
    if not branch_name or branch_name.isspace():
        click.echo("Branch name cannot be empty", err=True)
        sys.exit(1)
    
    if not task_description or task_description.isspace():
        click.echo("Task description cannot be empty", err=True)
        sys.exit(1)
    
    # Prepare volume mounts
    volumes = {
        str(project_root): {"bind": "/workspace", "mode": "rw"},
        str(Path.home() / ".claude"): {"bind": "/root/.claude", "mode": "rw"},
        str(Path.home() / ".config/claude"): {"bind": "/root/.config/claude", "mode": "rw"},
        str(Path.home() / ".ssh"): {"bind": "/root/.ssh", "mode": "ro"}  # For git operations
    }
    
    container = None
    try:
        click.echo(f"\nStarting task on branch '{branch_name}'...")
        
        # Create container (without --rm so it persists)
        container = docker_client.client.containers.run(
            image_name,
            command="sleep infinity",  # Keep container running
            volumes=volumes,
            working_dir="/workspace",
            environment={
                'CLAUDE_CONFIG_DIR': '/root/.claude',
                'NODE_OPTIONS': '--max-old-space-size=4096'
            },
            detach=True,
            labels={"claude-container": "true", "claude-container-type": "task"}
        )
        
        # Step 1: Checkout branch and pull
        click.echo(f"Checking out branch '{branch_name}'...")
        
        # Check if branch exists locally
        checkout_result = container.exec_run(
            f"git checkout -b {branch_name}",
            workdir="/workspace"
        )
        
        if checkout_result.exit_code != 0:
            # Branch might already exist, try just checking out
            checkout_result = container.exec_run(
                f"git checkout {branch_name}",
                workdir="/workspace"
            )
            
            if checkout_result.exit_code != 0:
                click.echo(f"Error checking out branch: {checkout_result.output.decode()}", err=True)
                raise Exception("Failed to checkout branch")
        
        # Pull latest changes
        container.exec_run(
            "git pull",
            workdir="/workspace"
        )
        
        # Step 2: Run Claude Code with the task description
        click.echo(f"\nRunning Claude Code with task: {task_description}")
        click.echo("This may take a while...\n")
        
        # Run Claude interactively
        claude_result = container.exec_run(
            ["claude", "--model=sonnet", "-p", task_description],
            workdir="/workspace",
            stream=True
        )
        
        # Stream output to user
        for chunk in claude_result.output:
            click.echo(chunk.decode(), nl=False)
        
        # Step 3: Commit changes
        click.echo("\n\nCommitting changes...")
        
        # Add all changes
        add_result = container.exec_run(
            "git add -A",
            workdir="/workspace"
        )
        
        if add_result.exit_code != 0:
            click.echo(f"Warning: git add failed: {add_result.output.decode()}")
        
        # Commit with static message for now
        commit_message = f"Task: {task_description}\n\nAutomated commit from claude-container task"
        commit_result = container.exec_run(
            ["git", "commit", "-m", commit_message],
            workdir="/workspace"
        )
        
        if commit_result.exit_code != 0:
            if b"nothing to commit" in commit_result.output:
                click.echo("No changes to commit")
            else:
                click.echo(f"Error committing: {commit_result.output.decode()}", err=True)
        else:
            click.echo("Changes committed successfully")
        
        # Push the branch
        click.echo(f"Pushing branch '{branch_name}'...")
        push_result = container.exec_run(
            f"git push -u origin {branch_name}",
            workdir="/workspace"
        )
        
        if push_result.exit_code != 0:
            click.echo(f"Error pushing branch: {push_result.output.decode()}", err=True)
            raise Exception("Failed to push branch")
        
        # Step 4: Create PR using gh CLI (run on host, not in container)
        click.echo("\nCreating pull request...")
        
        pr_title = f"Task: {branch_name}"
        pr_body = f"## Task Description\n{task_description}\n\n---\nThis PR was created automatically by claude-container task"
        
        try:
            pr_result = subprocess.run(
                [
                    "gh", "pr", "create",
                    "--title", pr_title,
                    "--body", pr_body,
                    "--head", branch_name,
                    "--draft"
                ],
                capture_output=True,
                text=True,
                check=True
            )
            
            click.echo("Pull request created successfully!")
            click.echo(pr_result.stdout)
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            click.echo(f"Error creating PR: {error_msg}", err=True)
            click.echo("Make sure you have the GitHub CLI installed and authenticated")
        
        click.echo(f"\n✓ Task completed successfully on branch '{branch_name}'")
        
    except Exception as e:
        click.echo(f"Error during task execution: {e}", err=True)
        sys.exit(1)
        
    finally:
        # Step 5: Cleanup - remove container
        if container:
            try:
                click.echo("\nCleaning up container...")
                container.stop()
                container.remove()
                click.echo("Container removed")
            except Exception as e:
                click.echo(f"Warning: Failed to remove container: {e}", err=True)


@task.command()
def list():
    """List all tasks"""
    client = DaemonClient()
    response = client.list_tasks()
    
    if "error" in response:
        click.echo(f"Error: {response['error']}", err=True)
        return
    
    tasks = response.get("tasks", [])
    if not tasks:
        click.echo("No tasks found")
        return
    
    click.echo(f"Found {len(tasks)} task(s):")
    for task_info in tasks:
        click.echo(f"  - {task_info['id']}: {task_info['state']} - {' '.join(task_info['command'])}")


@task.command()
@click.argument('task_id')
def status(task_id):
    """Get status of a specific task"""
    client = DaemonClient()
    response = client.get_status(task_id)
    
    if "error" in response:
        click.echo(f"Error: {response['error']}", err=True)
        return
    
    click.echo(f"Task {task_id}:")
    click.echo(f"  State: {response.get('state', 'unknown')}")
    click.echo(f"  Command: {' '.join(response.get('command', []))}")
    click.echo(f"  Working Directory: {response.get('working_dir', 'unknown')}")
    
    if response.get('started_at'):
        click.echo(f"  Started: {response['started_at']}")
    if response.get('completed_at'):
        click.echo(f"  Completed: {response['completed_at']}")


@task.command()
@click.argument('task_id')
def output(task_id):
    """Get output of a task"""
    client = DaemonClient()
    response = client.get_output(task_id)
    
    if "error" in response:
        click.echo(f"Error: {response['error']}", err=True)
        return
    
    output = response.get("output", "")
    if output:
        click.echo(output)
    else:
        click.echo("No output available")