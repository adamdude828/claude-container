"""Task command for Claude Container."""

import click
import subprocess
import sys
import tempfile
import os
from pathlib import Path
from datetime import datetime

from ...core.container_runner import ContainerRunner
from ...core.constants import CONTAINER_PREFIX, DATA_DIR_NAME, DEFAULT_WORKDIR, LIBERAL_SETTINGS_JSON
from ...core.task_storage import TaskStorageManager
from ...models.task import TaskStatus
from ..commands.auth_check import check_claude_auth


def get_description_from_editor():
    """Open editor for user to write task description with fallback."""
    # Template for task description
    template = """# Task Description
# Please describe the task you want Claude to complete.
# Lines starting with '#' will be removed.
# 
# Consider including:
# - What feature or bug fix is needed
# - Any specific requirements or constraints
# - Expected outcome or success criteria
#
# Example:
# Implement a user authentication system with email/password login,
# including registration, login, and logout endpoints. Use JWT tokens
# for session management.

"""
    
    # Get editor from environment or default to vim
    editor = os.environ.get('EDITOR', 'vim')
    
    # Create temporary file
    fd, temp_path = tempfile.mkstemp(suffix='.md', text=True)
    try:
        # Write template to temp file
        with os.fdopen(fd, 'w') as f:
            f.write(template)
        
        # Open editor - use subprocess.run for better error handling
        try:
            result = subprocess.run([editor, temp_path], check=False)
            
            if result.returncode != 0:
                return None
        except FileNotFoundError:
            click.echo(f"Error: Editor '{editor}' not found. Falling back to prompt.")
            return None
        except Exception as e:
            click.echo(f"Error opening editor: {e}. Falling back to prompt.")
            return None
        
        # Read contents
        with open(temp_path, 'r') as f:
            content = f.read()
        
        # Remove comment lines and clean up
        lines = [line for line in content.split('\n') if not line.strip().startswith('#')]
        description = '\n'.join(lines).strip()
        
        # Check if description is empty after removing comments
        if not description:
            click.echo("Description is empty. Falling back to prompt.")
            return None
            
        return description
    except Exception as e:
        click.echo(f"Error: {e}. Falling back to prompt.")
        return None
    finally:
        # Clean up temp file if it still exists
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def get_feedback_from_editor(initial_content=""):
    """Open editor for user to write feedback."""
    template = f"""# Task Feedback
# Please provide feedback or additional requirements for the task.
# Lines starting with '#' will be removed.
#
# Consider including:
# - What changes or improvements are needed
# - Any issues to address
# - Additional requirements or clarifications
#

{initial_content}
"""
    
    editor = os.environ.get('EDITOR', 'vim')
    fd, temp_path = tempfile.mkstemp(suffix='.md', text=True)
    
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(template)
        
        try:
            result = subprocess.run([editor, temp_path], check=False)
            if result.returncode != 0:
                return None
        except Exception:
            return None
        
        with open(temp_path, 'r') as f:
            content = f.read()
        
        lines = [line for line in content.split('\n') if not line.strip().startswith('#')]
        feedback = '\n'.join(lines).strip()
        
        if not feedback:
            return None
            
        return feedback
    except Exception:
        return None
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def format_task_list_item(task):
    """Format a task for list display."""
    # Truncate description to first line, max 50 chars
    desc_line = task.description.split('\n')[0]
    if len(desc_line) > 50:
        desc_line = desc_line[:47] + "..."
    
    # Format status with color
    status_colors = {
        TaskStatus.CREATED: 'green',
        TaskStatus.CONTINUED: 'yellow',
        TaskStatus.FAILED: 'red'
    }
    status_display = click.style(
        task.status.value.upper(), 
        fg=status_colors.get(task.status, 'white')
    )
    
    # Format dates
    created = task.created_at.strftime('%Y-%m-%d %H:%M')
    
    # Build output line
    parts = [
        f"{task.id[:8]}",  # Short ID
        f"{status_display:<15}",
        f"{task.branch_name:<30}",
        f"{desc_line:<50}",
        f"{created}"
    ]
    
    if task.pr_url:
        parts.append(click.style(" [PR]", fg='cyan'))
    
    if task.continuation_count > 0:
        parts.append(click.style(f" (cont: {task.continuation_count})", fg='yellow'))
    
    return " ".join(parts)


@click.group()
def task():
    """Manage Claude tasks"""
    pass


@task.command()
@click.option('--branch', '-b', help='Git branch name for the task')
@click.option('--file', '-f', 'description_file', type=click.Path(exists=True), 
              help='File containing task description')
def create(branch, description_file):
    """Create a new task and run it to completion"""
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
    
    # Initialize storage manager
    storage_manager = TaskStorageManager(data_dir)
    
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
    
    # Create task record
    task_metadata = storage_manager.create_task(task_description, branch)
    click.echo(f"\n✅ Created task {task_metadata.id[:8]} on branch '{branch}'")
    
    container = None
    try:
        click.echo(f"\n🚀 Starting task on branch '{branch}'...\n")
        
        # Update task status
        storage_manager.update_task(task_metadata.id, 
                                    started_at=datetime.now(),
                                    status=TaskStatus.CREATED)
        
        # Create persistent container for task execution
        container = container_runner.create_persistent_container("task")
        storage_manager.update_task(task_metadata.id, container_id=container.id)
        
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
        click.echo(f"\n🌿 Setting up branch '{branch}'...")
        
        # Attempt to create new branch
        checkout_result = container.exec_run(
            f"git checkout -b {branch}",
            workdir=DEFAULT_WORKDIR
        )
        
        if checkout_result.exit_code != 0:
            # Branch exists - switch to it
            checkout_result = container.exec_run(
                f"git checkout {branch}",
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
        
        # Build full output for logging
        claude_output = []
        
        # Execute Claude with the task
        claude_result = container.exec_run(
            ["claude", "--model=sonnet", "-p", task_description],
            workdir=DEFAULT_WORKDIR,
            stream=True
        )
        
        # Stream Claude's output in real-time
        for chunk in claude_result.output:
            decoded_chunk = chunk.decode()
            click.echo(decoded_chunk, nl=False)
            claude_output.append(decoded_chunk)
        
        # Save Claude output log
        storage_manager.save_task_log(task_metadata.id, "claude_output", ''.join(claude_output))
        
        # Step 3: Have Claude commit the changes
        click.echo("\n\n💾 Having Claude commit the changes...")
        
        # Check if there are changes to commit
        status_result = container.exec_run(
            "git status --porcelain",
            workdir=DEFAULT_WORKDIR
        )
        
        if not status_result.output.strip():
            click.echo("ℹ️  No changes to commit")
            commit_message = None
        else:
            # Ask Claude to commit the changes
            commit_prompt = f"Please commit all the changes you made. Review the changes with git diff and git status, then create a meaningful commit message that describes what was accomplished for the task: {task_description}"
            
            click.echo("\n🤖 Asking Claude to commit the changes...")
            click.echo("-" * 60 + "\n")
            
            commit_output = []
            commit_result = container.exec_run(
                ["claude", "--model=sonnet", "-p", commit_prompt],
                workdir=DEFAULT_WORKDIR,
                stream=True
            )
            
            # Stream Claude's commit output
            for chunk in commit_result.output:
                decoded_chunk = chunk.decode()
                click.echo(decoded_chunk, nl=False)
                commit_output.append(decoded_chunk)
            
            # Extract commit message from the last commit
            get_commit_msg = container.exec_run(
                "git log -1 --pretty=%B",
                workdir=DEFAULT_WORKDIR
            )
            
            if get_commit_msg.exit_code == 0:
                commit_message = get_commit_msg.output.decode().strip()
                click.echo("\n\n✅ Changes committed successfully")
                
                # Get commit hash
                get_commit_hash = container.exec_run(
                    "git rev-parse HEAD",
                    workdir=DEFAULT_WORKDIR
                )
                if get_commit_hash.exit_code == 0:
                    commit_hash = get_commit_hash.output.decode().strip()
                    storage_manager.update_task(task_metadata.id, commit_hash=commit_hash)
            else:
                click.echo("\n\n⚠️  Warning: Could not retrieve commit message")
                commit_message = f"Task: {task_description}"
        
        # Push to remote repository only if there was a commit
        if commit_message:
            click.echo(f"\n📤 Pushing branch '{branch}' to remote...")
            push_result = container.exec_run(
                f"git push -u origin {branch}",
                workdir=DEFAULT_WORKDIR
            )
            
            if push_result.exit_code != 0:
                click.echo(f"\n❌ Error: Failed to push branch\n{push_result.output.decode()}", err=True)
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
        if container:
            try:
                click.echo("\n🧹 Cleaning up resources...")
                container.stop()
                container.remove()
                click.echo("✅ Container removed successfully")
            except Exception as e:
                click.echo(f"⚠️  Warning: Failed to remove container: {e}", err=True)


@task.command(name='continue')
@click.argument('task_identifier')
@click.option('--feedback', '-f', help='Inline feedback string')
@click.option('--feedback-file', type=click.Path(exists=True), help='File containing feedback')
def continue_task(task_identifier, feedback, feedback_file):
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
    if not container_runner.docker_client.image_exists(image_name):
        click.echo(f"Error: Container image '{image_name}' not found.", err=True)
        sys.exit(1)
    
    container = None
    try:
        click.echo(f"\n🚀 Continuing task on branch '{task_metadata.branch_name}'...\n")
        
        # Create persistent container
        container = container_runner.create_persistent_container("task")
        storage_manager.update_task(task_metadata.id, container_id=container.id)
        
        # Configure Claude settings
        container.exec_run(f"mkdir -p {DEFAULT_WORKDIR}/.claude")
        write_cmd = f"echo '{LIBERAL_SETTINGS_JSON}' > {DEFAULT_WORKDIR}/.claude/settings.local.json"
        container.exec_run(["sh", "-c", write_cmd])
        
        # Checkout branch and pull latest
        click.echo(f"🌿 Checking out branch '{task_metadata.branch_name}'...")
        checkout_result = container.exec_run(
            f"git checkout {task_metadata.branch_name}",
            workdir=DEFAULT_WORKDIR
        )
        
        if checkout_result.exit_code != 0:
            click.echo(f"\n❌ Error: Failed to checkout branch\n{checkout_result.output.decode()}", err=True)
            raise Exception("Failed to checkout branch")
        
        click.echo("📥 Pulling latest changes...")
        container.exec_run("git pull", workdir=DEFAULT_WORKDIR)
        
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
        
        claude_output = []
        claude_result = container.exec_run(
            ["claude", "--model=sonnet", "-p", full_context],
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
            
            commit_result = container.exec_run(
                ["claude", "--model=sonnet", "-p", commit_prompt],
                workdir=DEFAULT_WORKDIR,
                stream=True
            )
            
            for chunk in commit_result.output:
                click.echo(chunk.decode(), nl=False)
            
            # Push changes
            click.echo(f"\n\n📤 Pushing changes to branch '{task_metadata.branch_name}'...")
            push_result = container.exec_run(
                "git push",
                workdir=DEFAULT_WORKDIR
            )
            
            if push_result.exit_code != 0:
                click.echo(f"\n⚠️  Warning: Failed to push\n{push_result.output.decode()}", err=True)
            else:
                click.echo("✅ Changes pushed successfully")
        
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


@task.command()
@click.option('--status', type=click.Choice(['created', 'continued', 'failed']), 
              help='Filter by task status')
def list(status):
    """List all tasks (both stored and running containers)"""
    from ...core.docker_client import DockerClient
    
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    # Show stored tasks
    if data_dir.exists():
        storage_manager = TaskStorageManager(data_dir)
        
        # Get tasks with optional status filter
        if status:
            tasks = storage_manager.list_tasks(TaskStatus(status))
        else:
            tasks = storage_manager.list_tasks()
        
        if tasks:
            click.echo(f"\n📋 Stored tasks for project '{project_root.name}':")
            click.echo("=" * 120)
            click.echo("ID       STATUS          BRANCH                         DESCRIPTION                                        CREATED")
            click.echo("-" * 120)
            
            for task_item in tasks:
                click.echo(format_task_list_item(task_item))
        else:
            click.echo(f"\nNo stored tasks found for project '{project_root.name}'")
    
    # Also show running containers
    try:
        docker_client = DockerClient()
        
        # List containers for this project
        containers = docker_client.list_task_containers(
            name_prefix=f"{CONTAINER_PREFIX}-task",
            project_name=project_root.name
        )
        
        if containers:
            click.echo("\n🐳 Running task containers:")
            click.echo("-" * 60)
            
            for container in containers:
                status_val = container.status
                name = container.name
                created = container.attrs['Created'][:19]
                
                # Color code status
                if status_val == 'running':
                    status_display = click.style(status_val.upper(), fg='green')
                elif status_val == 'exited':
                    status_display = click.style(status_val.upper(), fg='yellow')
                else:
                    status_display = click.style(status_val.upper(), fg='red')
                
                click.echo(f"{name:<40} {status_display:<10} {created}")
                
    except RuntimeError as e:
        click.echo(f"\n⚠️  Warning: Could not list Docker containers: {e}", err=True)


@task.command()
@click.argument('task_id')
@click.option('--feedback-history', is_flag=True, help='Show feedback history')
def show(task_id, feedback_history):
    """Show detailed information about a task"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    if not data_dir.exists():
        click.echo("Error: No container configuration found.", err=True)
        sys.exit(1)
    
    storage_manager = TaskStorageManager(data_dir)
    
    # Get task (support short IDs)
    task_metadata = storage_manager.get_task(task_id)
    if not task_metadata:
        # Try to find by short ID
        all_tasks = storage_manager.list_tasks()
        matching_tasks = [t for t in all_tasks if t.id.startswith(task_id)]
        if len(matching_tasks) == 1:
            task_metadata = matching_tasks[0]
        elif len(matching_tasks) > 1:
            click.echo(f"Error: Multiple tasks found starting with '{task_id}'", err=True)
            sys.exit(1)
        else:
            click.echo(f"Error: No task found with ID: {task_id}", err=True)
            sys.exit(1)
    
    # Display task details
    click.echo("\n" + "=" * 80)
    click.echo(f"Task Details: {task_metadata.id}")
    click.echo("=" * 80)
    
    click.echo("\n📋 Basic Information:")
    click.echo(f"   ID: {task_metadata.id}")
    click.echo(f"   Status: {click.style(task_metadata.status.value.upper(), fg='yellow')}")
    click.echo(f"   Branch: {task_metadata.branch_name}")
    click.echo(f"   Created: {task_metadata.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if task_metadata.started_at:
        click.echo(f"   Started: {task_metadata.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if task_metadata.completed_at:
        click.echo(f"   Completed: {task_metadata.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if task_metadata.last_continued_at:
        click.echo(f"   Last Continued: {task_metadata.last_continued_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    click.echo(f"   Continuations: {task_metadata.continuation_count}")
    
    if task_metadata.pr_url:
        click.echo("\n🔗 Pull Request:")
        click.echo(f"   {task_metadata.pr_url}")
    
    if task_metadata.commit_hash:
        click.echo("\n📝 Last Commit:")
        click.echo(f"   {task_metadata.commit_hash}")
    
    click.echo("\n📄 Description:")
    for line in task_metadata.description.split('\n'):
        click.echo(f"   {line}")
    
    if task_metadata.error_message:
        click.echo("\n❌ Error:")
        click.echo(f"   {task_metadata.error_message}")
    
    if feedback_history and task_metadata.feedback_history:
        click.echo("\n💬 Feedback History:")
        for i, entry in enumerate(task_metadata.feedback_history, 1):
            click.echo(f"\n   [{i}] {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')} ({entry.feedback_type})")
            for line in entry.feedback.split('\n'):
                click.echo(f"       {line}")


@task.command()
@click.argument('task_id')
@click.confirmation_option(prompt='Are you sure you want to delete this task?')
def delete(task_id):
    """Delete a task and all associated data"""
    project_root = Path.cwd()
    data_dir = project_root / DATA_DIR_NAME
    
    if not data_dir.exists():
        click.echo("Error: No container configuration found.", err=True)
        sys.exit(1)
    
    storage_manager = TaskStorageManager(data_dir)
    
    # Get task to verify it exists
    task_metadata = storage_manager.get_task(task_id)
    if not task_metadata:
        # Try short ID
        all_tasks = storage_manager.list_tasks()
        matching_tasks = [t for t in all_tasks if t.id.startswith(task_id)]
        if len(matching_tasks) == 1:
            task_metadata = matching_tasks[0]
            task_id = task_metadata.id
        elif len(matching_tasks) > 1:
            click.echo(f"Error: Multiple tasks found starting with '{task_id}'", err=True)
            sys.exit(1)
        else:
            click.echo(f"Error: No task found with ID: {task_id}", err=True)
            sys.exit(1)
    
    # Delete the task
    storage_manager.delete_task(task_id)
    
    click.echo(f"✅ Task {task_id[:8]} deleted successfully")
    click.echo(f"   Branch: {task_metadata.branch_name}")
    click.echo(f"   Description: {task_metadata.description.split(chr(10))[0]}...")


# Keep the old 'start' command for backward compatibility, but hidden
@task.command(hidden=True)
def start():
    """(Deprecated) Use 'task create' instead"""
    click.echo("This command is deprecated. Please use 'claude-container task create' instead.")
    ctx = click.get_current_context()
    ctx.invoke(create)


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