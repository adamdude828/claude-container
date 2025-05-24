"""Task command for Claude Container."""

import click
import subprocess
import sys
from pathlib import Path

from ...core.daemon_client import DaemonClient


@click.group()
def task():
    """Manage Claude tasks"""
    pass


@task.command()
def start():
    """Start a new task with branch and PR creation"""
    # Prompt for branch name
    branch_name = click.prompt("Enter the branch name for this task")
    
    # Validate branch name
    if not branch_name or branch_name.isspace():
        click.echo("Branch name cannot be empty", err=True)
        return
    
    # Create the feature branch using git
    click.echo(f"Creating branch '{branch_name}'...")
    
    try:
        # Check if branch already exists
        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout.strip():
            click.echo(f"Branch '{branch_name}' already exists")
            # Checkout existing branch
            subprocess.run(
                ["git", "checkout", branch_name],
                check=True
            )
        else:
            # Create and checkout new branch
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                check=True
            )
            click.echo(f"Created and switched to branch '{branch_name}'")
    
    except subprocess.CalledProcessError as e:
        click.echo(f"Error creating branch: {e}", err=True)
        return
    
    # Create PR using gh CLI
    click.echo("Creating pull request...")
    
    try:
        # Push the branch first (even if empty)
        subprocess.run(
            ["git", "push", "-u", "origin", branch_name],
            check=True
        )
        
        # Create PR
        pr_title = f"Task: {branch_name}"
        pr_body = f"This PR was created for task on branch '{branch_name}'"
        
        result = subprocess.run(
            [
                "gh", "pr", "create",
                "--title", pr_title,
                "--body", pr_body,
                "--head", branch_name,
                "--draft"  # Create as draft PR
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        click.echo("Pull request created successfully!")
        click.echo(result.stdout)
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        click.echo(f"Error creating PR: {error_msg}", err=True)
        click.echo("Make sure you have the GitHub CLI installed and authenticated")
        return
    
    click.echo(f"\nTask started on branch '{branch_name}' with PR created")
    click.echo("You can now begin working on your task")


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