"""Task command for Claude Container."""

import click
import subprocess
import sys
import re
import logging
from pathlib import Path
from datetime import datetime

from ...core.daemon_client import DaemonClient

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
def task():
    """Manage Claude tasks"""
    pass


@task.command()
def start():
    """Start a new task with branch creation"""
    logger.info("Starting task:start command")
    
    # Check daemon connectivity first
    try:
        logger.debug("Creating DaemonClient instance")
        client = DaemonClient()
        # Test connection by listing tasks
        logger.debug("Testing daemon connection by listing tasks")
        response = client.list_tasks()
        logger.debug(f"Daemon connection test response: {response}")
        
        if "error" in response:
            raise ConnectionError(f"Daemon error: {response['error']}")
            
    except (ConnectionError, Exception) as e:
        logger.error(f"Failed to connect to daemon: {e}")
        click.echo(f"Error: Cannot connect to daemon - is it running?", err=True)
        click.echo(f"Start the daemon with: claude-container daemon start", err=True)
        sys.exit(1)
    
    # Prompt for branch name
    branch = click.prompt("Enter the branch name for this task")
    
    # Validate branch name
    if not branch or branch.isspace():
        click.echo("Branch name cannot be empty", err=True)
        return
    
    # Prompt for task description
    task_description = click.prompt("Enter the task description")
    
    # Validate task description
    if not task_description or task_description.isspace():
        click.echo("Task description cannot be empty", err=True)
        return
    
    click.echo(f"Task: {task_description}")
    click.echo(f"Branch: {branch}")
    
    # Get current branch to return to if needed
    try:
        current_branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        current_branch = current_branch_result.stdout.strip()
    except subprocess.CalledProcessError:
        current_branch = None
    
    # Create the feature branch using git
    click.echo(f"Creating branch '{branch}'...")
    
    try:
        # Check if branch already exists
        result = subprocess.run(
            ["git", "branch", "--list", branch],
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout.strip():
            click.echo(f"Branch '{branch}' already exists")
            # Checkout existing branch
            subprocess.run(
                ["git", "checkout", branch],
                check=True
            )
        else:
            # Create and checkout new branch
            subprocess.run(
                ["git", "checkout", "-b", branch],
                check=True
            )
            click.echo(f"Created and switched to branch '{branch}'")
    
    except subprocess.CalledProcessError as e:
        click.echo(f"Error creating branch: {e}", err=True)
        return
    
    # Push the branch to remote (empty branch is OK)
    click.echo("Pushing branch to remote...")
    
    try:
        subprocess.run(
            ["git", "push", "-u", "origin", branch],
            check=True
        )
        click.echo(f"Branch '{branch}' pushed to remote")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error pushing branch: {e}", err=True)
        click.echo("Note: PR will be created after task completion")
        # Continue anyway, PR can be created later
    
    # Start the async task with Claude
    click.echo("\nStarting Claude task...")
    
    # Prepare the Claude command with the task prompt
    claude_prompt = f"""You are working on the following task: {task_description}

You are currently on branch: {branch}

Please follow these steps:
1. Check if the branch '{branch}' is created and you are on it
2. If not on the branch, switch to it
3. Complete the task as described
4. When done, commit your changes to the branch with a descriptive commit message

Remember to:
- Make atomic commits with clear messages
- Test your changes before committing
- Follow the project's coding standards"""
    
    # Start the task asynchronously with metadata
    working_dir = subprocess.run(["pwd"], capture_output=True, text=True).stdout.strip()
    logger.info(f"Submitting task to daemon: branch={branch}, working_dir={working_dir}")
    logger.debug(f"Task metadata: branch={branch}, task_description={task_description}, type=feature_task")
    
    try:
        response = client.submit_task(
            command=["claude-code", "-p", claude_prompt],
            working_dir=working_dir,
            env=None,
            metadata={
                "branch": branch,
                "task_description": task_description,
                "type": "feature_task"
            }
        )
        logger.debug(f"Task submission response: {response}")
    except Exception as e:
        logger.error(f"Exception during task submission: {e}", exc_info=True)
        click.echo(f"Error submitting task to daemon: {e}", err=True)
        return
    
    if "error" in response:
        click.echo(f"Error starting Claude task: {response['error']}", err=True)
        # Return to original branch if task failed to start
        if current_branch:
            subprocess.run(["git", "checkout", current_branch], check=True)
        return
    
    task_id = response.get("task_id")
    click.echo(f"\nTask started successfully!")
    click.echo(f"Task ID: {task_id}")
    click.echo(f"Branch: {branch}")
    click.echo(f"Description: {task_description}")
    click.echo(f"\nPR will be created automatically after task completion")
    click.echo(f"\nYou can check the task status with: claude-container task status {task_id}")
    click.echo(f"You can see the task output with: claude-container task output {task_id}")


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