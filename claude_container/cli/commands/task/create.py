"""Create task command."""

import click
import subprocess
import sys
from datetime import datetime

from claude_container.cli.helpers import (
    ensure_authenticated,
    get_storage_and_runner,
    cleanup_container
)
from ....core.constants import DEFAULT_WORKDIR, LIBERAL_SETTINGS_JSON
from ....models.task import TaskStatus
from ...util import get_description_from_editor


@click.command()
@click.option('--branch', '-b', help='Git branch name for the task')
@click.option('--file', '-f', 'description_file', type=click.Path(exists=True), 
              help='File containing task description')
def create(branch, description_file):
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
        
        # Create new branch
        checkout_result = container.exec_run(
            f"git checkout -b {branch}",
            workdir=DEFAULT_WORKDIR
        )
        
        if checkout_result.exit_code != 0:
            click.echo(f"\n❌ Error: Failed to create branch\n{checkout_result.output.decode()}", err=True)
            raise Exception("Failed to create branch")
        
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
            
            # Save commit output
            storage_manager.save_task_log(task_metadata.id, "claude_commit", ''.join(commit_output))
            
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
        cleanup_container(container)