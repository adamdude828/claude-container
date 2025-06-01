"""Show task command."""

import click

from claude_container.cli.helpers import ensure_container_built, get_project_context, resolve_task_id

from ....core.task_storage import TaskStorageManager


@click.command()
@click.argument('task_id')
@click.option('--feedback-history', is_flag=True, help='Show feedback history')
def show(task_id, feedback_history):
    """Show detailed information about a task"""
    project_root, data_dir = get_project_context()
    ensure_container_built(data_dir)

    storage_manager = TaskStorageManager(data_dir)

    # Get task (support short IDs)
    task_metadata = resolve_task_id(storage_manager, task_id)

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
