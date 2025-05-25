"""Tests for GitHub integration."""
import subprocess
from unittest.mock import patch, MagicMock
import pytest

from claude_container.core.github_integration import GitHubIntegration


class TestGitHubIntegration:
    """Test suite for GitHubIntegration."""
    
    @pytest.fixture
    def github(self):
        """Create a GitHubIntegration instance."""
        return GitHubIntegration('/test/project')
    
    @patch('os.chdir')
    @patch('subprocess.run')
    def test_get_pr_for_branch_exists(self, mock_run, mock_chdir, github):
        """Test getting PR URL when PR exists for branch."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"url": "https://github.com/user/repo/pull/1"}]',
            stderr=''
        )
        
        pr_url = github.get_pr_for_branch('feature-branch')
        
        assert pr_url == 'https://github.com/user/repo/pull/1'
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert 'gh' in call_args
        assert 'pr' in call_args
        assert 'list' in call_args
        assert '--head' in call_args
        assert 'feature-branch' in call_args
    
    @patch('os.chdir')
    @patch('subprocess.run')
    def test_get_pr_for_branch_not_exists(self, mock_run, mock_chdir, github):
        """Test getting PR URL when no PR exists for branch."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[]',
            stderr=''
        )
        
        pr_url = github.get_pr_for_branch('feature-branch')
        
        assert pr_url is None
    
    @patch('os.chdir')
    @patch('subprocess.run')
    def test_get_pr_for_branch_error(self, mock_run, mock_chdir, github):
        """Test getting PR URL when gh command fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'gh', stderr='Error')
        
        pr_url = github.get_pr_for_branch('feature-branch')
        
        assert pr_url is None
    
    @patch('subprocess.run')
    @patch('os.chdir')
    def test_create_pull_request_success(self, mock_chdir, mock_run, github):
        """Test successful PR creation."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='https://github.com/user/repo/pull/2',
            stderr=''
        )
        
        pr_url = github.create_pull_request(
            branch_name='feature-branch',
            title='Add new feature',
            body='Feature description',
            draft=False
        )
        
        assert pr_url == 'https://github.com/user/repo/pull/2'
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert 'gh' in call_args
        assert 'pr' in call_args
        assert 'create' in call_args
        assert '--title' in call_args
        assert 'Add new feature' in call_args
        assert '--body' in call_args
        assert 'Feature description' in call_args
    
    @patch('subprocess.run')
    @patch('os.chdir')
    def test_create_pull_request_draft(self, mock_chdir, mock_run, github):
        """Test creating a draft PR."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='https://github.com/user/repo/pull/3',
            stderr=''
        )
        
        pr_url = github.create_pull_request(
            branch_name='feature-branch',
            title='WIP: Add feature',
            body='Work in progress',
            draft=True
        )
        
        assert pr_url == 'https://github.com/user/repo/pull/3'
        call_args = mock_run.call_args[0][0]
        assert '--draft' in call_args
    
    @patch('subprocess.run')
    @patch('os.chdir')
    def test_create_pull_request_failure(self, mock_chdir, mock_run, github):
        """Test PR creation failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'gh', stderr='Pull request already exists'
        )
        
        pr_url = github.create_pull_request(
            branch_name='feature-branch',
            title='Add feature',
            body='Description'
        )
        
        assert pr_url is None