"""Git service for abstracting Git operations."""

import logging
import subprocess
from pathlib import Path
from typing import Optional

from .exceptions import BranchNotFoundError, GitServiceError

logger = logging.getLogger(__name__)


class GitService:
    """Service for Git operations with clean abstractions."""

    def __init__(self, repo_path: Optional[Path] = None):
        """Initialize Git service.

        Args:
            repo_path: Path to the git repository (defaults to current directory)
        """
        self.repo_path = repo_path or Path.cwd()
        if not self._is_git_repo():
            raise GitServiceError(f"{self.repo_path} is not a git repository")

    def _is_git_repo(self) -> bool:
        """Check if the current path is a git repository."""
        try:
            self._run_git_command(["rev-parse", "--git-dir"])
            return True
        except GitServiceError:
            return False

    def _run_git_command(
        self, args: list[str], check: bool = True, capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a git command with proper error handling.

        Args:
            args: Git command arguments
            check: Check return code
            capture_output: Capture stdout and stderr

        Returns:
            Completed process result

        Raises:
            GitServiceError: If command fails
        """
        cmd = ["git"] + args
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                check=check,
                capture_output=capture_output,
                text=True,
            )
            return result
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise GitServiceError(f"Git command failed: {error_msg}") from e
        except Exception as e:
            raise GitServiceError(f"Unexpected error running git command: {e}") from e

    def checkout_branch(self, branch_name: str, create: bool = False) -> None:
        """Checkout a git branch.

        Args:
            branch_name: Name of the branch
            create: Create branch if it doesn't exist

        Raises:
            BranchNotFoundError: If branch doesn't exist and create=False
            GitServiceError: If checkout fails
        """
        if not create and not self.branch_exists_local(branch_name):
            raise BranchNotFoundError(f"Branch '{branch_name}' not found locally")

        try:
            args = ["checkout"]
            if create:
                args.append("-b")
            args.append(branch_name)
            self._run_git_command(args)
            logger.info(f"Checked out branch: {branch_name}")
        except GitServiceError as e:
            if "already exists" in str(e):
                # Branch already exists, just checkout
                self._run_git_command(["checkout", branch_name])
            else:
                raise

    def push_branch(
        self, branch_name: Optional[str] = None, set_upstream: bool = False
    ) -> None:
        """Push a branch to remote.

        Args:
            branch_name: Branch name (defaults to current branch)
            set_upstream: Set upstream tracking

        Raises:
            GitServiceError: If push fails
        """
        args = ["push"]
        if set_upstream:
            args.extend(["-u", "origin"])
        if branch_name:
            args.extend(["origin", branch_name])

        self._run_git_command(args)
        logger.info(f"Pushed branch: {branch_name or 'current'}")

    def commit_all_changes(self, message: str) -> None:
        """Stage all changes and commit.

        Args:
            message: Commit message

        Raises:
            GitServiceError: If commit fails
        """
        # Check if there are changes to commit
        status_result = self._run_git_command(["status", "--porcelain"])
        if not status_result.stdout.strip():
            logger.info("No changes to commit")
            return

        # Stage all changes
        self._run_git_command(["add", "-A"])

        # Commit
        self._run_git_command(["commit", "-m", message])
        logger.info(f"Committed changes: {message}")

    def branch_exists_local(self, branch_name: str) -> bool:
        """Check if a branch exists locally.

        Args:
            branch_name: Name of the branch

        Returns:
            True if branch exists locally
        """
        try:
            result = self._run_git_command(
                ["branch", "--list", branch_name], check=False
            )
            return bool(result.stdout.strip())
        except GitServiceError:
            return False

    def branch_exists_remote(self, branch_name: str, remote: str = "origin") -> bool:
        """Check if a branch exists on remote.

        Args:
            branch_name: Name of the branch
            remote: Remote name

        Returns:
            True if branch exists on remote
        """
        try:
            # Fetch remote branch info
            self._run_git_command(["fetch", remote, branch_name], check=False)
            result = self._run_git_command(
                ["ls-remote", "--heads", remote, branch_name], check=False
            )
            return bool(result.stdout.strip())
        except GitServiceError:
            return False

    def get_current_branch(self) -> str:
        """Get the current branch name.

        Returns:
            Current branch name

        Raises:
            GitServiceError: If unable to get branch
        """
        result = self._run_git_command(["branch", "--show-current"])
        branch = result.stdout.strip()
        if not branch:
            raise GitServiceError("Unable to determine current branch")
        return branch

    def get_remote_url(self, remote: str = "origin") -> str:
        """Get the URL of a remote.

        Args:
            remote: Remote name

        Returns:
            Remote URL

        Raises:
            GitServiceError: If remote not found
        """
        result = self._run_git_command(["remote", "get-url", remote])
        return result.stdout.strip()

    def create_tag(self, tag_name: str, message: Optional[str] = None) -> None:
        """Create a git tag.

        Args:
            tag_name: Name of the tag
            message: Tag message (creates annotated tag if provided)

        Raises:
            GitServiceError: If tag creation fails
        """
        args = ["tag"]
        if message:
            args.extend(["-a", tag_name, "-m", message])
        else:
            args.append(tag_name)

        self._run_git_command(args)
        logger.info(f"Created tag: {tag_name}")

    def delete_branch(self, branch_name: str, force: bool = False) -> None:
        """Delete a local branch.

        Args:
            branch_name: Name of the branch
            force: Force delete even if not merged

        Raises:
            BranchNotFoundError: If branch doesn't exist
            GitServiceError: If deletion fails
        """
        if not self.branch_exists_local(branch_name):
            raise BranchNotFoundError(f"Branch '{branch_name}' not found locally")

        args = ["branch", "-d" if not force else "-D", branch_name]
        self._run_git_command(args)
        logger.info(f"Deleted branch: {branch_name}")

    def get_commit_hash(self, ref: str = "HEAD") -> str:
        """Get the commit hash of a reference.

        Args:
            ref: Git reference (default: HEAD)

        Returns:
            Commit hash

        Raises:
            GitServiceError: If unable to get hash
        """
        result = self._run_git_command(["rev-parse", ref])
        return result.stdout.strip()

    def get_uncommitted_changes(self) -> list[str]:
        """Get list of files with uncommitted changes.

        Returns:
            List of file paths with changes
        """
        result = self._run_git_command(["status", "--porcelain"])
        if not result.stdout.strip():
            return []

        files = []
        for line in result.stdout.rstrip().split('\n'):
            if line:
                # Status format: "XY filename" where XY are two status characters
                # followed by a space, then the filename
                files.append(line[3:])
        return files

    def stash_changes(self, message: Optional[str] = None) -> None:
        """Stash current changes.

        Args:
            message: Stash message

        Raises:
            GitServiceError: If stash fails
        """
        args = ["stash", "push"]
        if message:
            args.extend(["-m", message])

        self._run_git_command(args)
        logger.info("Stashed changes")

    def stash_pop(self) -> None:
        """Pop the most recent stash.

        Raises:
            GitServiceError: If pop fails
        """
        self._run_git_command(["stash", "pop"])
        logger.info("Popped stash")
