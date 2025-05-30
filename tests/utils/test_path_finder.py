"""Tests for path_finder.py module."""

import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from claude_container.utils.path_finder import PathFinder


class TestPathFinder:
    """Test suite for PathFinder class."""
    
    def test_find_claude_code_in_predefined_paths(self, tmp_path):
        """Test finding Claude Code in predefined paths."""
        # Create a fake claude executable
        claude_path = tmp_path / "claude"
        claude_path.touch()
        
        with patch('claude_container.utils.path_finder.CLAUDE_CODE_PATHS', [str(claude_path)]):
            result = PathFinder.find_claude_code()
            assert result == str(claude_path)
    
    def test_find_claude_code_with_which_command(self):
        """Test finding Claude Code using which command."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "/usr/local/bin/claude\n"
        
        with patch('claude_container.utils.path_finder.CLAUDE_CODE_PATHS', []):
            with patch('subprocess.run', return_value=mock_result):
                result = PathFinder.find_claude_code()
                assert result == "/usr/local/bin/claude"
    
    def test_find_claude_code_in_path(self, tmp_path):
        """Test finding Claude Code in PATH."""
        claude_path = tmp_path / "claude"
        claude_path.touch()
        
        with patch('claude_container.utils.path_finder.CLAUDE_CODE_PATHS', []):
            with patch('subprocess.run', side_effect=Exception()):
                with patch.dict(os.environ, {'PATH': str(tmp_path)}):
                    result = PathFinder.find_claude_code()
                    assert result == str(claude_path)
    
    def test_find_claude_code_not_found(self):
        """Test when Claude Code is not found."""
        with patch('claude_container.utils.path_finder.CLAUDE_CODE_PATHS', []):
            with patch('subprocess.run', side_effect=Exception()):
                with patch.dict(os.environ, {'PATH': ''}):
                    result = PathFinder.find_claude_code()
                    assert result is None
    
    def test_detect_project_type_python(self, tmp_path):
        """Test detecting Python project."""
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.touch()
        
        result = PathFinder.detect_project_type(tmp_path)
        assert result == "python"
    
    def test_detect_project_type_node(self, tmp_path):
        """Test detecting Node.js project."""
        package_json = tmp_path / "package.json"
        package_json.touch()
        
        result = PathFinder.detect_project_type(tmp_path)
        assert result == "node"
    
    def test_detect_project_type_default(self, tmp_path):
        """Test detecting default project type when no patterns match."""
        result = PathFinder.detect_project_type(tmp_path)
        assert result == "default"
    
    def test_check_git_ssh_origin_with_ssh(self):
        """Test checking Git SSH origin with SSH URL."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "git@github.com:user/repo.git\n"
        
        with patch('subprocess.run', return_value=mock_result):
            result = PathFinder.check_git_ssh_origin(Path("."))
            assert result is True
    
    def test_check_git_ssh_origin_with_https(self):
        """Test checking Git SSH origin with HTTPS URL."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/user/repo.git\n"
        
        with patch('subprocess.run', return_value=mock_result):
            result = PathFinder.check_git_ssh_origin(Path("."))
            assert result is False
    
    def test_check_git_ssh_origin_no_remote(self):
        """Test checking Git SSH origin when no remote exists."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        
        with patch('subprocess.run', return_value=mock_result):
            result = PathFinder.check_git_ssh_origin(Path("."))
            assert result is True  # No git repo, allow to proceed
    
    def test_check_git_ssh_origin_exception(self):
        """Test checking Git SSH origin when subprocess fails."""
        with patch('subprocess.run', side_effect=Exception()):
            result = PathFinder.check_git_ssh_origin(Path("."))
            assert result is True  # If git check fails, allow to proceed
    
    def test_find_claude_code_which_command_fails(self):
        """Test finding Claude Code when which command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        
        with patch('claude_container.utils.path_finder.CLAUDE_CODE_PATHS', []):
            with patch('subprocess.run', return_value=mock_result):
                with patch.dict(os.environ, {'PATH': ''}):
                    result = PathFinder.find_claude_code()
                    assert result is None