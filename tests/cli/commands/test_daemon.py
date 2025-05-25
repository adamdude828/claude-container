"""Tests for the daemon command."""
import os
import time
from unittest.mock import patch, MagicMock, mock_open
import pytest
from click.testing import CliRunner
from pathlib import Path

from claude_container.cli.commands.daemon import daemon


class TestDaemonCommand:
    """Test suite for daemon commands."""
    
    def test_daemon_help(self, cli_runner):
        """Test daemon help command."""
        result = cli_runner.invoke(daemon, ['--help'])
        assert result.exit_code == 0
        assert 'Manage the Claude task daemon' in result.output
    
    @patch('claude_container.cli.commands.daemon.subprocess.Popen')
    @patch('claude_container.cli.commands.daemon.Path.home')
    @patch('claude_container.cli.commands.daemon.DaemonClient')
    @patch('os.kill')
    def test_daemon_start_success(self, mock_kill, mock_daemon_client, mock_home, mock_popen, cli_runner):
        """Test successful daemon start."""
        # Setup mocks
        mock_home.return_value = Path('/mock/home')
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        # Mock daemon client to simulate successful connection
        mock_client = MagicMock()
        mock_client.list_tasks.return_value = {'tasks': []}
        mock_daemon_client.return_value = mock_client
        
        # Mock os.kill to indicate process is running
        mock_kill.return_value = None
        
        # Mock file operations
        with patch('builtins.open', mock_open()):
            with patch('claude_container.cli.commands.daemon.Path.exists', return_value=False):
                with patch('claude_container.cli.commands.daemon.Path.mkdir'):
                    with patch('claude_container.cli.commands.daemon.Path.write_text'):
                        result = cli_runner.invoke(daemon, ['start'])
        
        assert result.exit_code == 0
        assert 'Daemon started successfully' in result.output
        assert 'PID 12345' in result.output
    
    @patch('claude_container.cli.commands.daemon.Path.home')
    @patch('os.kill')
    def test_daemon_stop_success(self, mock_kill, mock_home, cli_runner):
        """Test successful daemon stop."""
        mock_home.return_value = Path('/mock/home')
        
        # Mock PID file exists and contains PID
        with patch('claude_container.cli.commands.daemon.Path.exists', return_value=True):
            with patch('claude_container.cli.commands.daemon.Path.read_text', return_value='12345'):
                with patch('claude_container.cli.commands.daemon.Path.unlink'):
                    result = cli_runner.invoke(daemon, ['stop'])
        
        assert result.exit_code == 0
        assert 'Daemon (PID 12345) stopped' in result.output
        mock_kill.assert_called_once_with(12345, 15)  # SIGTERM
    
    @patch('claude_container.cli.commands.daemon.Path.home')
    def test_daemon_stop_no_pid_file(self, mock_home, cli_runner):
        """Test daemon stop when no PID file exists."""
        mock_home.return_value = Path('/mock/home')
        
        with patch('claude_container.cli.commands.daemon.Path.exists', return_value=False):
            result = cli_runner.invoke(daemon, ['stop'])
        
        assert result.exit_code == 0
        assert 'No daemon PID file found' in result.output
    
    @patch('claude_container.cli.commands.daemon.Path.home')
    @patch('claude_container.cli.commands.daemon.DaemonClient')
    @patch('os.kill')
    def test_daemon_status_running(self, mock_kill, mock_daemon_client, mock_home, cli_runner):
        """Test daemon status when daemon is running."""
        mock_home.return_value = Path('/mock/home')
        
        # Mock daemon client
        mock_client = MagicMock()
        mock_client.list_tasks.return_value = {'tasks': [{'id': 'task-1'}, {'id': 'task-2'}]}
        mock_daemon_client.return_value = mock_client
        
        # Mock process is running
        mock_kill.return_value = None
        
        with patch('claude_container.cli.commands.daemon.Path.exists', return_value=True):
            with patch('claude_container.cli.commands.daemon.Path.read_text', return_value='12345'):
                result = cli_runner.invoke(daemon, ['status'])
        
        assert result.exit_code == 0
        assert 'Daemon running with PID 12345' in result.output
        assert 'Active tasks: 2' in result.output
    
    @patch('claude_container.cli.commands.daemon.Path.home')
    def test_daemon_status_not_running(self, mock_home, cli_runner):
        """Test daemon status when daemon is not running."""
        mock_home.return_value = Path('/mock/home')
        
        with patch('claude_container.cli.commands.daemon.Path.exists', return_value=False):
            result = cli_runner.invoke(daemon, ['status'])
        
        assert result.exit_code == 0
        assert 'Daemon not running' in result.output