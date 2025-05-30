# Task Start Editor Implementation Plan

## Overview
Implement editor support for task descriptions when running `claude-container task start`. The user should be prompted to enter a description in their configured editor (defaulting to vim if not specified).

## Requirements
1. When `claude-container task start` is run, open an editor for the user to write the task description
2. Editor runs on host system, description is passed to container
3. Still prompt for branch name separately (as currently implemented)
4. Fall back to simple prompt if editor fails
5. Provide a template to guide task description writing

## Implementation Details

### 1. Editor Selection Logic
- Check for `EDITOR` environment variable first
- Fall back to vim as default
- Run editor on host system (outside Docker container)

### 2. Temporary File Handling
- Create a temporary file with `.md` extension for the description
- Pre-populate with a helpful template
- Open the editor with this file
- Read the contents after editor closes
- Clean up the temporary file

### 3. Integration Points
- Modify `claude_container/cli/commands/task.py` to add editor support
- Update the `task_start` function to use editor for description before container creation
- Keep the branch name prompt as-is
- Pass the collected description to container as before

### 4. Error Handling
- If editor fails to open or user cancels, fall back to simple `click.prompt()`
- Handle empty descriptions (prompt user to retry or use simple prompt)
- Ensure temporary files are cleaned up even on error

### 5. Template Design
- Provide clear guidance on what to include
- Use markdown formatting
- Include commented instructions that will be stripped

## Code Changes Required

### File: `claude_container/cli/commands/task.py`
1. Import required modules for temporary file handling and subprocess
2. Add function to open editor and get description with fallback
3. Modify `task_start` to use editor instead of simple input prompt

### Example Implementation Flow
```python
def get_description_from_editor():
    """Open editor for user to write task description with fallback."""
    import tempfile
    import subprocess
    import os
    
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
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        temp_path = f.name
        f.write(template)
    
    try:
        # Open editor
        result = subprocess.call([editor, temp_path])
        
        if result != 0:
            # Editor failed or user cancelled, fall back to prompt
            os.unlink(temp_path)
            return None
        
        # Read contents
        with open(temp_path, 'r') as f:
            content = f.read()
        
        # Remove comment lines and clean up
        lines = [line for line in content.split('\n') if not line.strip().startswith('#')]
        description = '\n'.join(lines).strip()
        
        # Check if description is empty after removing comments
        if not description:
            os.unlink(temp_path)
            return None
            
        return description
    except Exception:
        # Any error, fall back to prompt
        return None
    finally:
        # Clean up temp file if it still exists
        if os.path.exists(temp_path):
            os.unlink(temp_path)

# In task_start function:
# Replace: task_description = click.prompt("Task description")
# With:
task_description = get_description_from_editor()
if task_description is None:
    # Fall back to simple prompt
    task_description = click.prompt("Task description")
```

## Testing Plan
1. Test with EDITOR environment variable set to different editors
2. Test with no EDITOR variable (should use vim)
3. Test canceling editor (Ctrl+C or :q! in vim)
4. Test empty descriptions
5. Test multi-line descriptions with formatting

## Future Enhancements
- Add `--editor` flag to override default editor for single command
- Add persistent editor configuration in claude-container config
- Support for GUI editors (may require additional handling)

## Success Criteria
- User can write multi-line descriptions comfortably in their preferred editor
- Workflow feels natural and similar to git commit message editing
- No breaking changes to existing task functionality
- Proper error handling and cleanup