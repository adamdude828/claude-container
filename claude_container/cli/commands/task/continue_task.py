"""Continue task command."""

import click
import sys
from pathlib import Path
from datetime import datetime

from ....core.container_runner import ContainerRunner
from ....core.constants import CONTAINER_PREFIX, DATA_DIR_NAME, DEFAULT_WORKDIR, LIBERAL_SETTINGS_JSON
from ....core.task_storage import TaskStorageManager
from ....models.task import TaskStatus
from ...commands.auth_check import check_claude_auth
from ...util import get_feedback_from_editor


@click.command(name='continue')
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
            
            commit_output = []
            commit_result = container.exec_run(
                ["claude", "--model=sonnet", "-p", commit_prompt],
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