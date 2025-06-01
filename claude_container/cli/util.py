"""Shared utility functions for CLI commands."""

import click

from claude_container.cli.helpers import open_in_editor


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

    content = open_in_editor(template)

    if not content:
        click.echo("Description is empty or editor failed. Falling back to prompt.")
        return None

    # Remove comment lines and clean up
    lines = [line for line in content.split('\n') if not line.strip().startswith('#')]
    description = '\n'.join(lines).strip()

    # Check if description is empty after removing comments
    if not description:
        click.echo("Description is empty. Falling back to prompt.")
        return None

    return description


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

    content = open_in_editor(template)

    if not content:
        return None

    lines = [line for line in content.split('\n') if not line.strip().startswith('#')]
    feedback = '\n'.join(lines).strip()

    if not feedback:
        return None

    return feedback
