"""Task command for Claude Container."""

import click
import subprocess
import sys
from pathlib import Path

from ...core.container_runner import ContainerRunner
from ...core.constants import CONTAINER_PREFIX, DATA_DIR_NAME, DEFAULT_WORKDIR, LIBERAL_SETTINGS_JSON
from ..commands.auth_check import check_claude_auth


@click.group()
def task():
    """Manage Claude tasks"""
    pass


@task.command()
def list():
    """List all task containers for the current project"""
    from ...core.docker_client import DockerClient
    from ...core.constants import CONTAINER_PREFIX
    
    project_root = Path.cwd()
    
    try:
        docker_client = DockerClient()
        
        # List containers for this project
        containers = docker_client.list_task_containers(
            name_prefix=f"{CONTAINER_PREFIX}-task",
            project_name=project_root.name
        )
        
        if not containers:
            click.echo("No task containers found for this project")
            return
        
        click.echo(f"Task containers for project '{project_root.name}':")
        click.echo("-" * 60)
        
        for container in containers:
            status = container.status
            name = container.name
            created = container.attrs['Created'][:19]  # Truncate to readable format
            
            # Color code status
            if status == 'running':
                status_display = click.style(status.upper(), fg='green')
            elif status == 'exited':
                status_display = click.style(status.upper(), fg='yellow')
            else:
                status_display = click.style(status.upper(), fg='red')
            
            click.echo(f"{name:<40} {status_display:<10} {created}")
            
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


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
        
        # Copy liberal settings.local.json to project's .claude directory
        # Create .claude directory in workspace if it doesn't exist
        container.exec_run(f"mkdir -p {DEFAULT_WORKDIR}/.claude")
        
        # Write settings.local.json to workspace .claude directory
        write_cmd = f"echo '{LIBERAL_SETTINGS_JSON}' > {DEFAULT_WORKDIR}/.claude/settings.local.json"
        settings_result = container.exec_run(["sh", "-c", write_cmd])
        
        if settings_result.exit_code != 0:
            click.echo("Warning: Failed to write settings.local.json to project", err=True)
        
        # Also add .claude/settings.local.json to .gitignore if not already there
        gitignore_check = container.exec_run(
            f"grep -q '^.claude/settings.local.json$' {DEFAULT_WORKDIR}/.gitignore",
            workdir=DEFAULT_WORKDIR
        )
        
        if gitignore_check.exit_code != 0:
            # Not in .gitignore, add it
            container.exec_run(
                f"echo '.claude/settings.local.json' >> {DEFAULT_WORKDIR}/.gitignore",
                workdir=DEFAULT_WORKDIR
            )
        
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


@task.command()
def debug_settings():
    """Debug command to verify settings.local.json setup"""
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
    
    container = None
    try:
        click.echo("Creating temporary container for debug...")
        container = container_runner.create_persistent_container("debug")
        
        # Create .claude directory
        click.echo("\n1. Creating .claude directory in workspace...")
        mkdir_result = container.exec_run(f"mkdir -p {DEFAULT_WORKDIR}/.claude")
        click.echo(f"   Result: {mkdir_result.exit_code} - {mkdir_result.output.decode()}")
        
        # Write settings file
        click.echo("\n2. Writing settings.local.json...")
        write_cmd = f"echo '{LIBERAL_SETTINGS_JSON}' > {DEFAULT_WORKDIR}/.claude/settings.local.json"
        write_result = container.exec_run(["sh", "-c", write_cmd])
        click.echo(f"   Result: {write_result.exit_code} - {write_result.output.decode()}")
        
        # Check if file was created
        click.echo("\n3. Checking if file exists...")
        check_result = container.exec_run(f"ls -la {DEFAULT_WORKDIR}/.claude/")
        click.echo(f"   Result: {check_result.exit_code}")
        click.echo(f"   Output:\n{check_result.output.decode()}")
        
        # Read file contents
        click.echo("\n4. Reading file contents...")
        read_result = container.exec_run(f"cat {DEFAULT_WORKDIR}/.claude/settings.local.json")
        click.echo(f"   Result: {read_result.exit_code}")
        click.echo(f"   Contents:\n{read_result.output.decode()}")
        
        # Check Claude's home directory
        click.echo("\n5. Checking Claude's home directory...")
        home_result = container.exec_run("ls -la /home/node/.claude/")
        click.echo(f"   Result: {home_result.exit_code}")
        click.echo(f"   Output:\n{home_result.output.decode()}")
        
        click.echo("\nDebug complete!")
        
    except Exception as e:
        click.echo(f"Error during debug: {e}", err=True)
        sys.exit(1)
    finally:
        if container:
            try:
                container.stop()
                container.remove()
                click.echo("Cleaned up debug container.")
            except Exception:
                pass


