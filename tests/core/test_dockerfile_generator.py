import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from claude_container.core.dockerfile_generator import DockerfileGenerator
from claude_container.models.container import ContainerConfig


class TestDockerfileGenerator:
    """Smoke tests for DockerfileGenerator functionality."""
    
    def test_dockerfile_generator_initialization(self, temp_project_dir):
        """Test that DockerfileGenerator initializes correctly."""
        generator = DockerfileGenerator(temp_project_dir)
        assert generator.project_root == temp_project_dir
    
    @patch('claude_container.core.dockerfile_generator.ConfigManager')
    @patch('claude_container.core.dockerfile_generator.generate_dockerfile')
    def test_generate_with_claude(self, mock_generate_dockerfile, mock_config_manager_class, temp_project_dir):
        """Test generating Dockerfile with Claude."""
        # Setup mocks
        mock_config_manager = MagicMock()
        mock_config = ContainerConfig(base_image="python:3.10")
        mock_config_manager.get_container_config.return_value = mock_config
        mock_config_manager_class.return_value = mock_config_manager
        
        mock_generate_dockerfile.return_value = "FROM python:3.10\nWORKDIR /app"
        
        # Test
        generator = DockerfileGenerator(temp_project_dir)
        result = generator.generate_with_claude("/path/to/claude")
        
        # Verify
        assert "FROM python:3.10" in result
        mock_generate_dockerfile.assert_called_once_with(mock_config)
    
    @patch('claude_container.core.dockerfile_generator.ConfigManager')
    @patch('claude_container.core.dockerfile_generator.generate_dockerfile')
    def test_generate_cached(self, mock_generate_dockerfile, mock_config_manager_class, temp_project_dir):
        """Test generating cached Dockerfile."""
        # Setup mocks
        mock_config_manager = MagicMock()
        mock_config = ContainerConfig(base_image="node:18")
        mock_config_manager.get_container_config.return_value = mock_config
        mock_config_manager_class.return_value = mock_config_manager
        
        mock_generate_dockerfile.return_value = "FROM node:18\nCOPY . /app"
        
        # Test
        generator = DockerfileGenerator(temp_project_dir)
        result = generator.generate_cached(include_code=True)
        
        # Verify
        assert "FROM node:18" in result
        assert mock_config.include_code is True
        mock_generate_dockerfile.assert_called_once()