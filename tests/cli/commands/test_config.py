import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from claude_container.cli.commands.config import config, env, runtime, show, reset


class TestConfigCommand:
    """Smoke tests for config command."""
    
    def test_config_command_help(self, cli_runner):
        """Test config command shows help."""
        result = cli_runner.invoke(config, ['--help'])
        
        assert result.exit_code == 0
        assert "Manage container configuration" in result.output
        assert "env" in result.output
        assert "runtime" in result.output
        assert "show" in result.output
    
    @patch('claude_container.cli.commands.config.ConfigManager')
    def test_config_env_command(self, mock_config_manager_class, cli_runner):
        """Test setting environment variable."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        
        result = cli_runner.invoke(config, ['env', 'NODE_ENV', 'production'])
        
        assert result.exit_code == 0
        assert "Set environment variable: NODE_ENV=production" in result.output
        mock_manager.update_env_vars.assert_called_once_with({'NODE_ENV': 'production'})
    
    @patch('claude_container.cli.commands.config.ConfigManager')
    def test_config_runtime_command(self, mock_config_manager_class, cli_runner):
        """Test setting runtime version."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        
        result = cli_runner.invoke(config, ['runtime', 'python', '3.11'])
        
        assert result.exit_code == 0
        assert "Set python version to 3.11" in result.output
        mock_manager.add_runtime_version.assert_called_once_with('python', '3.11')
    
    @patch('claude_container.cli.commands.config.ConfigManager')
    def test_config_show_command(self, mock_config_manager_class, cli_runner):
        """Test showing configuration."""
        from claude_container.models.container import ContainerConfig
        
        mock_manager = MagicMock()
        mock_config = ContainerConfig(
            base_image="python:3.10",
            env_vars={"TEST": "value"}
        )
        mock_manager.get_container_config.return_value = mock_config
        mock_config_manager_class.return_value = mock_manager
        
        result = cli_runner.invoke(config, ['show'])
        
        assert result.exit_code == 0
        assert "Container Configuration:" in result.output
        assert "python:3.10" in result.output
        assert "TEST" in result.output
    
    @patch('claude_container.cli.commands.config.ConfigManager')
    def test_config_show_no_config(self, mock_config_manager_class, cli_runner):
        """Test showing configuration when none exists."""
        mock_manager = MagicMock()
        mock_manager.get_container_config.return_value = None
        mock_config_manager_class.return_value = mock_manager
        
        result = cli_runner.invoke(config, ['show'])
        
        assert result.exit_code == 0
        assert "No container configuration found" in result.output
    
    @patch('claude_container.cli.commands.config.ConfigManager')
    def test_config_reset_command(self, mock_config_manager_class, cli_runner):
        """Test resetting configuration."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        
        result = cli_runner.invoke(config, ['reset'])
        
        assert result.exit_code == 0
        assert "Container configuration reset to defaults" in result.output
        mock_manager.save_container_config.assert_called_once()
    
    def test_config_runtime_invalid_choice(self, cli_runner):
        """Test runtime command with invalid runtime name."""
        result = cli_runner.invoke(config, ['runtime', 'invalid', '1.0'])
        
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "Error" in result.output