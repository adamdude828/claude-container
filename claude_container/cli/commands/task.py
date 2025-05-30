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
    """Start a new task with Claude authentication check."""
    # Verify Claude authentication
    if not check_claude_auth():
        sys.exit(1)
    
    # Initialize project configuration
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    # Validate container environment
    if not data_dir.exists():
        click.echo("Error: No container found. Please run 'claude-container build' first.", err=True)
        sys.exit(1)
    
    image_name = f"{CONTAINER_PREFIX}-{project_root.name}".lower()
    
    # Initialize container runner
    try:
        container_runner = ContainerRunner(project_root, data_dir, image_name)
    except RuntimeError as e:
        click.echo(f"Error initializing container: {e}", err=True)
        sys.exit(1)
    
    # Verify container image exists
    if not container_runner.docker_client.image_exists(image_name):
        click.echo(f"Error: Container image '{image_name}' not found.", err=True)
        click.echo("Please run 'claude-container build' first.")
        sys.exit(1)
    
    # Collect task parameters
    click.echo("\n" + "=" * 60)
    click.echo("Claude Container Task Setup")
    click.echo("=" * 60 + "\n")
    
    branch_name = click.prompt("Branch name")
    task_description = click.prompt("Task description")
    
    # Validate user inputs
    if not branch_name or branch_name.isspace():
        click.echo("\nError: Branch name cannot be empty.", err=True)
        sys.exit(1)
    
    if not task_description or task_description.isspace():
        click.echo("\nError: Task description cannot be empty.", err=True)
        sys.exit(1)
    
    container = None
    try:
        click.echo(f"\n🚀 Starting task on branch '{branch_name}'...\n")
        
        # Create persistent container for task execution
        container = container_runner.create_persistent_container("task")
        
        # Configure Claude settings for the project
        click.echo("📝 Configuring Claude settings...")
        
        # Create .claude directory in workspace
        container.exec_run(f"mkdir -p {DEFAULT_WORKDIR}/.claude")
        
        # Write liberal settings configuration
        write_cmd = f"echo '{LIBERAL_SETTINGS_JSON}' > {DEFAULT_WORKDIR}/.claude/settings.local.json"
        settings_result = container.exec_run(["sh", "-c", write_cmd])
        
        if settings_result.exit_code != 0:
            click.echo("⚠️  Warning: Failed to write settings.local.json", err=True)
        
        # Update .gitignore to exclude settings file
        gitignore_check = container.exec_run(
            f"grep -q '^.claude/settings.local.json$' {DEFAULT_WORKDIR}/.gitignore",
            workdir=DEFAULT_WORKDIR
        )
        
        if gitignore_check.exit_code != 0:
            container.exec_run(
                f"echo '.claude/settings.local.json' >> {DEFAULT_WORKDIR}/.gitignore",
                workdir=DEFAULT_WORKDIR
            )
        
        # Step 1: Git branch setup
        click.echo(f"\n🌿 Setting up branch '{branch_name}'...")
        
        # Attempt to create new branch
        checkout_result = container.exec_run(
            f"git checkout -b {branch_name}",
            workdir=DEFAULT_WORKDIR
        )
        
        if checkout_result.exit_code != 0:
            # Branch exists - switch to it
            checkout_result = container.exec_run(
                f"git checkout {branch_name}",
                workdir=DEFAULT_WORKDIR
            )
            
            if checkout_result.exit_code != 0:
                click.echo(f"\n❌ Error: Failed to checkout branch\n{checkout_result.output.decode()}", err=True)
                raise Exception("Failed to checkout branch")
        
        # Sync with remote
        click.echo("📥 Pulling latest changes...")
        container.exec_run(
            "git pull",
            workdir=DEFAULT_WORKDIR
        )
        
        # Step 2: Execute Claude task
        click.echo(f"\n🤖 Running Claude with task:\n   {task_description}")
        click.echo("\n" + "-" * 60)
        click.echo("Claude is working on your task...")
        click.echo("-" * 60 + "\n")
        
        # Execute Claude with the task
        claude_result = container.exec_run(
            ["claude", "--model=sonnet", "-p", task_description],
            workdir=DEFAULT_WORKDIR,
            stream=True
        )
        
        # Stream Claude's output in real-time
        for chunk in claude_result.output:
            click.echo(chunk.decode(), nl=False)
        
        # Step 3: Commit changes
        click.echo("\n\n💾 Committing changes...")
        
        # Stage all changes
        add_result = container.exec_run(
            "git add -A",
            workdir=DEFAULT_WORKDIR
        )
        
        if add_result.exit_code != 0:
            click.echo(f"⚠️  Warning: Failed to stage changes: {add_result.output.decode()}")
        
        # Create commit with descriptive message
        commit_message = f"Task: {task_description}\n\nAutomated commit from claude-container task"
        commit_result = container.exec_run(
            ["git", "commit", "-m", commit_message],
            workdir=DEFAULT_WORKDIR
        )
        
        if commit_result.exit_code != 0:
            if b"nothing to commit" in commit_result.output:
                click.echo("ℹ️  No changes to commit")
            else:
                click.echo(f"❌ Error: Commit failed\n{commit_result.output.decode()}", err=True)
        else:
            click.echo("✅ Changes committed successfully")
        
        # Push to remote repository
        click.echo(f"\n📤 Pushing branch '{branch_name}' to remote...")
        push_result = container.exec_run(
            f"git push -u origin {branch_name}",
            workdir=DEFAULT_WORKDIR
        )
        
        if push_result.exit_code != 0:
            click.echo(f"\n❌ Error: Failed to push branch\n{push_result.output.decode()}", err=True)
            raise Exception("Failed to push branch")
        
        # Step 4: Create pull request
        click.echo("\n🔀 Creating pull request...")
        
        pr_title = f"Task: {branch_name}"
        pr_body = f"## 📋 Task Description\n\n{task_description}\n\n---\n\n*This PR was created automatically by claude-container task*"
        
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
            
            click.echo("\n✅ Pull request created successfully!")
            click.echo(pr_result.stdout)
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            click.echo(f"\n❌ Error: Failed to create PR\n{error_msg}", err=True)
            click.echo("\nℹ️  Make sure you have the GitHub CLI installed and authenticated")
        
        click.echo("\n🎉 Task completed successfully!")
        click.echo(f"   Branch: {branch_name}")
        click.echo("   Status: Ready for review")
        
    except Exception as e:
        click.echo(f"\n❌ Error during task execution: {e}", err=True)
        sys.exit(1)
        
    finally:
        # Step 5: Cleanup
        if container:
            try:
                click.echo("\n🧹 Cleaning up resources...")
                container.stop()
                container.remove()
                click.echo("✅ Container removed successfully")
            except Exception as e:
                click.echo(f"⚠️  Warning: Failed to remove container: {e}", err=True)


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


