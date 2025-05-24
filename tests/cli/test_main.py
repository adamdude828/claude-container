import pytest
from click.testing import CliRunner
from claude_container.cli.main import cli


class TestMainCLI:
    """Smoke tests for main CLI functionality."""
    
    def test_cli_help(self, cli_runner):
        """Test that CLI shows help."""
        result = cli_runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Claude Container' in result.output
        assert 'Commands:' in result.output
    
    def test_cli_no_args(self, cli_runner):
        """Test CLI with no arguments shows help."""
        result = cli_runner.invoke(cli, [])
        assert result.exit_code == 2  # Click returns 2 for missing command
        assert 'Usage:' in result.output
    
    def test_cli_invalid_command(self, cli_runner):
        """Test CLI with invalid command."""
        result = cli_runner.invoke(cli, ['invalid-command'])
        assert result.exit_code != 0
        assert 'Error' in result.output or 'No such command' in result.output
    
    def test_cli_command_groups(self, cli_runner):
        """Test that main command groups are available."""
        result = cli_runner.invoke(cli, ['--help'])
        
        # Check for main commands
        expected_commands = ['build', 'run', 'clean', 'config', 'daemon', 'queue']
        for cmd in expected_commands:
            assert cmd in result.output