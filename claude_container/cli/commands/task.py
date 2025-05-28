"""Task command for Claude Container."""

import click
import subprocess
import sys
from pathlib import Path

from ...core.container_runner import ContainerRunner
from ...core.constants import CONTAINER_PREFIX, DATA_DIR_NAME, DEFAULT_WORKDIR
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
    
    image_name = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
    
    try:
        container_runner = ContainerRunner(project_root, data_dir, image_name)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    
    # Check if image exists
    if not container_runner.docker_client.image_exists(image_name):
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
    
    container = None
    try:
        click.echo(f"\nStarting task on branch '{branch_name}'...")
        
        # Create persistent container using ContainerRunner
        container = container_runner.create_persistent_container("task")
        
        # Step 1: Checkout branch and pull
        click.echo(f"Checking out branch '{branch_name}'...")
        
        # Check if branch exists locally
        checkout_result = container.exec_run(
            f"git checkout -b {branch_name}",
            workdir=DEFAULT_WORKDIR
        )
        
        if checkout_result.exit_code != 0:
            # Branch might already exist, try just checking out
            checkout_result = container.exec_run(
                f"git checkout {branch_name}",
                workdir=DEFAULT_WORKDIR
            )
            
            if checkout_result.exit_code != 0:
                click.echo(f"Error checking out branch: {checkout_result.output.decode()}", err=True)
                raise Exception("Failed to checkout branch")
        
        # Pull latest changes
        container.exec_run(
            "git pull",
            workdir=DEFAULT_WORKDIR
        )
        
        # Step 2: Run Claude Code with the task description
        click.echo(f"\nRunning Claude Code with task: {task_description}")
        click.echo("This may take a while...\n")
        
        # Run Claude interactively
        claude_result = container.exec_run(
            ["claude", "--model=sonnet", "-p", task_description],
            workdir=DEFAULT_WORKDIR,
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
            workdir=DEFAULT_WORKDIR
        )
        
        if add_result.exit_code != 0:
            click.echo(f"Warning: git add failed: {add_result.output.decode()}")
        
        # Commit with static message for now
        commit_message = f"Task: {task_description}\n\nAutomated commit from claude-container task"
        commit_result = container.exec_run(
            ["git", "commit", "-m", commit_message],
            workdir=DEFAULT_WORKDIR
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
            workdir=DEFAULT_WORKDIR
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


