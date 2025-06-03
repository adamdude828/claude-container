"""Tests for Git service."""

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess
import pytest

from claude_container.services.git_service import GitService
from claude_container.services.exceptions import (
    GitServiceError,
    BranchNotFoundError,
)


class TestGitService:
    """Test cases for GitService."""

    @patch('claude_container.services.git_service.GitService._is_git_repo')
    def test_init_success(self, mock_is_git_repo):
        """Test successful initialization."""
        mock_is_git_repo.return_value = True
        service = GitService(Path("/test/repo"))
        assert service.repo_path == Path("/test/repo")

    @patch('claude_container.services.git_service.GitService._is_git_repo')
    def test_init_not_git_repo(self, mock_is_git_repo):
        """Test initialization in non-git directory."""
        mock_is_git_repo.return_value = False
        with pytest.raises(GitServiceError, match="is not a git repository"):
            GitService(Path("/test/repo"))

    @patch('subprocess.run')
    def test_run_git_command_success(self, mock_run):
        """Test successful git command execution."""
        mock_result = Mock()
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            result = service._run_git_command(["status"])

        assert result == mock_result
        mock_run.assert_called_once_with(
            ["git", "status"],
            cwd=service.repo_path,
            check=True,
            capture_output=True,
            text=True
        )

    @patch('subprocess.run')
    def test_run_git_command_failure(self, mock_run):
        """Test git command failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["git", "status"], stderr="error message"
        )

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            with pytest.raises(GitServiceError, match="Git command failed"):
                service._run_git_command(["status"])

    @patch('subprocess.run')
    def test_checkout_branch_success(self, mock_run):
        """Test successful branch checkout."""
        mock_run.return_value = Mock(stdout="", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            with patch.object(service, 'branch_exists_local', return_value=True):
                service.checkout_branch("feature-branch")

        mock_run.assert_called_with(
            ["git", "checkout", "feature-branch"],
            cwd=service.repo_path,
            check=True,
            capture_output=True,
            text=True
        )

    @patch('subprocess.run')
    def test_checkout_branch_create(self, mock_run):
        """Test creating and checking out new branch."""
        mock_run.return_value = Mock(stdout="", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            service.checkout_branch("new-branch", create=True)

        mock_run.assert_called_with(
            ["git", "checkout", "-b", "new-branch"],
            cwd=service.repo_path,
            check=True,
            capture_output=True,
            text=True
        )

    def test_checkout_branch_not_found(self):
        """Test checkout of non-existent branch."""
        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            with patch.object(service, 'branch_exists_local', return_value=False):
                with pytest.raises(BranchNotFoundError, match="Branch 'missing' not found"):
                    service.checkout_branch("missing")

    @patch('subprocess.run')
    def test_push_branch_success(self, mock_run):
        """Test successful branch push."""
        mock_run.return_value = Mock(stdout="", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            service.push_branch("feature-branch", set_upstream=True)

        mock_run.assert_called_with(
            ["git", "push", "-u", "origin", "origin", "feature-branch"],
            cwd=service.repo_path,
            check=True,
            capture_output=True,
            text=True
        )

    @patch('subprocess.run')
    def test_commit_all_changes_success(self, mock_run):
        """Test successful commit of all changes."""
        # First call for status, second for add, third for commit
        mock_run.side_effect = [
            Mock(stdout="M file.txt", stderr=""),  # status
            Mock(stdout="", stderr=""),  # add
            Mock(stdout="", stderr=""),  # commit
        ]

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            service.commit_all_changes("Test commit")

        assert mock_run.call_count == 3
        # Verify add and commit commands
        assert mock_run.call_args_list[1][0][0] == ["git", "add", "-A"]
        assert mock_run.call_args_list[2][0][0] == ["git", "commit", "-m", "Test commit"]

    @patch('subprocess.run')
    def test_commit_all_changes_no_changes(self, mock_run):
        """Test commit when no changes exist."""
        mock_run.return_value = Mock(stdout="", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            service.commit_all_changes("Test commit")

        # Only status should be called
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_branch_exists_local_true(self, mock_run):
        """Test checking if branch exists locally (true case)."""
        mock_run.return_value = Mock(stdout="  feature-branch", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            assert service.branch_exists_local("feature-branch") is True

    @patch('subprocess.run')
    def test_branch_exists_local_false(self, mock_run):
        """Test checking if branch exists locally (false case)."""
        mock_run.return_value = Mock(stdout="", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            assert service.branch_exists_local("missing-branch") is False

    @patch('subprocess.run')
    def test_branch_exists_remote_true(self, mock_run):
        """Test checking if branch exists on remote (true case)."""
        mock_run.side_effect = [
            Mock(stdout="", stderr=""),  # fetch
            Mock(stdout="refs/heads/feature-branch", stderr="")  # ls-remote
        ]

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            assert service.branch_exists_remote("feature-branch") is True

    @patch('subprocess.run')
    def test_branch_exists_remote_false(self, mock_run):
        """Test checking if branch exists on remote (false case)."""
        mock_run.side_effect = [
            Mock(stdout="", stderr=""),  # fetch
            Mock(stdout="", stderr="")  # ls-remote
        ]

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            assert service.branch_exists_remote("missing-branch") is False

    @patch('subprocess.run')
    def test_get_current_branch_success(self, mock_run):
        """Test getting current branch name."""
        mock_run.return_value = Mock(stdout="feature-branch\n", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            assert service.get_current_branch() == "feature-branch"

    @patch('subprocess.run')
    def test_get_current_branch_failure(self, mock_run):
        """Test failure to get current branch."""
        mock_run.return_value = Mock(stdout="", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            with pytest.raises(GitServiceError, match="Unable to determine current branch"):
                service.get_current_branch()

    @patch('subprocess.run')
    def test_get_remote_url_success(self, mock_run):
        """Test getting remote URL."""
        mock_run.return_value = Mock(stdout="https://github.com/user/repo.git\n", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            assert service.get_remote_url() == "https://github.com/user/repo.git"

    @patch('subprocess.run')
    def test_create_tag_simple(self, mock_run):
        """Test creating simple tag."""
        mock_run.return_value = Mock(stdout="", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            service.create_tag("v1.0.0")

        mock_run.assert_called_with(
            ["git", "tag", "v1.0.0"],
            cwd=service.repo_path,
            check=True,
            capture_output=True,
            text=True
        )

    @patch('subprocess.run')
    def test_create_tag_annotated(self, mock_run):
        """Test creating annotated tag."""
        mock_run.return_value = Mock(stdout="", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            service.create_tag("v1.0.0", message="Release version 1.0.0")

        mock_run.assert_called_with(
            ["git", "tag", "-a", "v1.0.0", "-m", "Release version 1.0.0"],
            cwd=service.repo_path,
            check=True,
            capture_output=True,
            text=True
        )

    @patch('subprocess.run')
    def test_delete_branch_success(self, mock_run):
        """Test successful branch deletion."""
        mock_run.return_value = Mock(stdout="", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            with patch.object(service, 'branch_exists_local', return_value=True):
                service.delete_branch("old-branch")

        mock_run.assert_called_with(
            ["git", "branch", "-d", "old-branch"],
            cwd=service.repo_path,
            check=True,
            capture_output=True,
            text=True
        )

    @patch('subprocess.run')
    def test_delete_branch_force(self, mock_run):
        """Test force branch deletion."""
        mock_run.return_value = Mock(stdout="", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            with patch.object(service, 'branch_exists_local', return_value=True):
                service.delete_branch("old-branch", force=True)

        mock_run.assert_called_with(
            ["git", "branch", "-D", "old-branch"],
            cwd=service.repo_path,
            check=True,
            capture_output=True,
            text=True
        )

    def test_delete_branch_not_found(self):
        """Test deleting non-existent branch."""
        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            with patch.object(service, 'branch_exists_local', return_value=False):
                with pytest.raises(BranchNotFoundError):
                    service.delete_branch("missing-branch")

    @patch('subprocess.run')
    def test_get_commit_hash_success(self, mock_run):
        """Test getting commit hash."""
        mock_run.return_value = Mock(stdout="abc123def456\n", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            assert service.get_commit_hash() == "abc123def456"

    @patch('subprocess.run')
    def test_get_uncommitted_changes(self, mock_run):
        """Test getting list of uncommitted changes."""
        # The _is_git_repo is patched, so mock_run is only called for get_uncommitted_changes
        mock_run.return_value = Mock(stdout=" M file1.txt\n?? file2.txt\n", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            changes = service.get_uncommitted_changes()

        assert changes == ["file1.txt", "file2.txt"]

    @patch('subprocess.run')
    def test_get_uncommitted_changes_empty(self, mock_run):
        """Test getting uncommitted changes when none exist."""
        mock_run.return_value = Mock(stdout="", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            assert service.get_uncommitted_changes() == []

    @patch('subprocess.run')
    def test_stash_changes_success(self, mock_run):
        """Test stashing changes."""
        mock_run.return_value = Mock(stdout="", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            service.stash_changes("WIP changes")

        mock_run.assert_called_with(
            ["git", "stash", "push", "-m", "WIP changes"],
            cwd=service.repo_path,
            check=True,
            capture_output=True,
            text=True
        )

    @patch('subprocess.run')
    def test_stash_pop_success(self, mock_run):
        """Test popping stash."""
        mock_run.return_value = Mock(stdout="", stderr="")

        with patch.object(GitService, '_is_git_repo', return_value=True):
            service = GitService()
            service.stash_pop()

        mock_run.assert_called_with(
            ["git", "stash", "pop"],
            cwd=service.repo_path,
            check=True,
            capture_output=True,
            text=True
        )