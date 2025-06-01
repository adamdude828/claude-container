"""GitHub integration for Claude Container."""

import os
import subprocess
from pathlib import Path
from typing import Optional

from ..services.exceptions import GitServiceError
from ..services.git_service import GitService


class GitHubIntegration:
    """Handle GitHub operations for Claude tasks."""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir).resolve()
        self.git_service = GitService(self.project_dir)

    def create_branch(self, branch_name: str) -> bool:
        """Create and push a new branch."""
        try:
            # Create and checkout branch
            self.git_service.checkout_branch(branch_name, create=True)

            # Push branch to origin
            self.git_service.push_branch(branch_name, set_upstream=True)

            return True
        except GitServiceError as e:
            print(f"Error creating branch: {e}")
            return False

    def create_pull_request(self, branch_name: str, title: str, body: str) -> Optional[str]:
        """Create a pull request and return its URL."""
        try:
            # Save current directory
            original_dir = os.getcwd()
            os.chdir(self.project_dir)

            # Create PR as draft
            result = subprocess.run([
                'gh', 'pr', 'create',
                '--title', title,
                '--body', body,
                '--draft',
                '--head', branch_name
            ], capture_output=True, text=True, check=True)

            # The URL is in stdout
            pr_url = result.stdout.strip()
            return pr_url

        except subprocess.CalledProcessError as e:
            print(f"Error creating PR: {e.stderr}")
            return None
        finally:
            os.chdir(original_dir)

    def update_pr_description(self, pr_number: str, description: str) -> bool:
        """Update PR description."""
        try:
            original_dir = os.getcwd()
            os.chdir(self.project_dir)

            subprocess.run([
                'gh', 'pr', 'edit', pr_number,
                '--body', description
            ], check=True, capture_output=True, text=True)

            return True
        except subprocess.CalledProcessError:
            return False
        finally:
            os.chdir(original_dir)

    def mark_pr_ready(self, pr_number: str) -> bool:
        """Mark PR as ready for review."""
        try:
            original_dir = os.getcwd()
            os.chdir(self.project_dir)

            subprocess.run([
                'gh', 'pr', 'ready', pr_number
            ], check=True, capture_output=True, text=True)

            return True
        except subprocess.CalledProcessError:
            return False
        finally:
            os.chdir(original_dir)

    def get_pr_number_from_url(self, pr_url: str) -> Optional[str]:
        """Extract PR number from URL."""
        # URL format: https://github.com/owner/repo/pull/123
        parts = pr_url.strip().split('/')
        if len(parts) >= 2 and parts[-2] == 'pull':
            return parts[-1]
        return None

    def check_git_status(self) -> tuple[bool, str]:
        """Check if git working directory is clean."""
        try:
            changes = self.git_service.get_uncommitted_changes()
            is_clean = len(changes) == 0
            status_msg = "" if is_clean else "\n".join(changes)
            return is_clean, status_msg

        except GitServiceError as e:
            return False, str(e)

    def get_current_branch(self) -> Optional[str]:
        """Get current git branch name."""
        try:
            return self.git_service.get_current_branch()
        except GitServiceError:
            return None
