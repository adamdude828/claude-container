"""Shared utility functions for CLI commands."""

import click
import subprocess
import tempfile
import os


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