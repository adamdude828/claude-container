import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from claude_container.core.container_runner import ContainerRunner


class TestContainerRunner:
    """Smoke tests for ContainerRunner functionality."""
    
    @patch('claude_container.core.container_runner.DockerService')
    def test_container_runner_initialization(self, mock_docker_service_class, temp_project_dir):
        """Test that ContainerRunner initializes correctly."""
        mock_docker = MagicMock()
        mock_docker_service_class.return_value = mock_docker
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        assert runner.project_root == temp_project_dir
        assert runner.data_dir == data_dir
        assert runner.image_name == "test-image"
        assert runner.docker_service == mock_docker
    
    @patch('claude_container.core.container_runner.DockerService')
    def test_run_command_image_not_exists(self, mock_docker_service_class, temp_project_dir, capsys):
        """Test running command when image doesn't exist."""
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = False
        mock_docker_service_class.return_value = mock_docker
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        runner.run_command(["echo", "hello"])
        
        captured = capsys.readouterr()
        assert "Docker image 'test-image' not found" in captured.out
        assert "Please run 'claude-container build' first" in captured.out
    
    @patch('claude_container.core.container_runner.DockerService')
    def test_run_command_success(self, mock_docker_service_class, temp_project_dir):
        """Test successful command run."""
        # Setup mocks
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = True
        mock_container = MagicMock()
        mock_container.decode.return_value = "Hello from container"
        mock_docker.run_container.return_value = b"Hello from container"
        mock_docker_service_class.return_value = mock_docker
        
        # Test
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        runner.run_command(["echo", "hello"])
        
        # Verify
        mock_docker.run_container.assert_called_once()
        call_kwargs = mock_docker.run_container.call_args[1]
        assert call_kwargs['working_dir'] == '/workspace'
        assert call_kwargs['remove'] is True
    
    
    @patch('claude_container.core.container_runner.DockerService')
    def test_create_persistent_container(self, mock_docker_service_class, temp_project_dir):
        """Test creating a persistent container for tasks."""
        # Setup mocks
        mock_docker = MagicMock()
        mock_container = MagicMock()
        mock_docker.run_container.return_value = mock_container
        mock_docker_service_class.return_value = mock_docker
        
        # Test
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        result = runner.create_persistent_container("task")
        
        # Verify
        assert result == mock_container
        mock_docker.run_container.assert_called_once()
        
        # Check configuration
        call_kwargs = mock_docker.run_container.call_args[1]
        assert call_kwargs['command'] == "sleep infinity"
        assert call_kwargs['detach'] is True
        assert call_kwargs['remove'] is False  # Should not auto-remove
        assert call_kwargs['working_dir'] == '/workspace'
        
        # Check container naming pattern
        container_name = call_kwargs['name']
        assert container_name.startswith('claude-container-task-')
        assert temp_project_dir.name.lower() in container_name
        # Should end with 8 character hex suffix
        parts = container_name.split('-')
        assert len(parts[-1]) == 8
        
        # Check labels
        assert call_kwargs['labels'] == {
            "claude-container": "true",
            "claude-container-type": "task",
            "claude-container-project": temp_project_dir.name.lower(),
            "claude-container-prefix": "claude-container"
        }
        
        # Check environment variables
        env = call_kwargs['environment']
        assert env['CLAUDE_CONFIG_DIR'] == '/root/.claude'
        assert env['HOME'] == '/root'
        assert env['NODE_OPTIONS'] == '--max-old-space-size=4096'
    
    def test_get_container_environment(self, temp_project_dir):
        """Test getting container environment variables."""
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        # Test without auto_approve
        env = runner._get_container_environment(auto_approve=False)
        assert env['CLAUDE_CONFIG_DIR'] == '/root/.claude'
        assert env['NODE_OPTIONS'] == '--max-old-space-size=4096'
        assert env['HOME'] == '/root'
        assert 'CLAUDE_AUTO_APPROVE' not in env
        
        # Test with auto_approve
        env = runner._get_container_environment(auto_approve=True)
        assert env['CLAUDE_AUTO_APPROVE'] == 'true'
    
    def test_get_container_config(self, temp_project_dir):
        """Test getting container configuration."""
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        # Test basic config
        config = runner._get_container_config()
        assert config['image'] == 'test-image'
        assert config['working_dir'] == '/workspace'
        assert config['tty'] is True
        assert config['stdin_open'] is True
        assert config['detach'] is False
        assert config['remove'] is True
        
        # Test with custom parameters
        config = runner._get_container_config(
            command=['echo', 'hello'],
            tty=False,
            stdin_open=False,
            detach=True,
            remove=False,
            stdout=True,
            stderr=True,
            auto_approve=True,
            name='test-container'
        )
        assert config['command'] == ['echo', 'hello']
        assert config['tty'] is False
        assert config['stdin_open'] is False
        assert config['detach'] is True
        assert config['remove'] is False
        assert config['stdout'] is True
        assert config['stderr'] is True
        assert config['name'] == 'test-container'
        assert config['environment']['CLAUDE_AUTO_APPROVE'] == 'true'
    
    @patch('claude_container.core.container_runner.Path')
    def test_get_volumes(self, mock_path_class, temp_project_dir):
        """Test getting volume mappings."""
        # Setup path mocks
        mock_home = MagicMock()
        mock_path_class.home.return_value = mock_home
        
        # Create mock paths that exist
        claude_dir = MagicMock()
        claude_dir.exists.return_value = True
        
        # Create .config mock that supports division
        config_dir = MagicMock()
        config_claude = MagicMock()
        config_claude.exists.return_value = True
        config_dir.__truediv__ = MagicMock(return_value=config_claude)
        
        # Map paths
        path_map = {
            '.claude': claude_dir,
            '.claude.json': MagicMock(exists=lambda: True),
            '.config': config_dir,
            '.ssh': MagicMock(exists=lambda: True)
        }
        
        mock_home.__truediv__ = MagicMock(side_effect=lambda x: path_map.get(x, MagicMock(exists=lambda: False)))
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        volumes = runner._get_volumes()
        
        # Project directory should be mounted
        assert str(temp_project_dir) in volumes
        assert volumes[str(temp_project_dir)]['bind'] == '/workspace'
        assert volumes[str(temp_project_dir)]['mode'] == 'rw'
    
    @patch('claude_container.core.container_runner.subprocess.run')
    def test_run_interactive_container(self, mock_subprocess_run, temp_project_dir):
        """Test running interactive container with subprocess."""
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        runner._run_interactive_container(['bash'])
        
        # Verify subprocess.run was called
        mock_subprocess_run.assert_called_once()
        docker_cmd = mock_subprocess_run.call_args[0][0]
        
        # Check basic docker command structure
        assert docker_cmd[0] == 'docker'
        assert docker_cmd[1] == 'run'
        assert '--rm' in docker_cmd
        assert '-it' in docker_cmd
        assert '-w' in docker_cmd
        assert '/workspace' in docker_cmd
        assert 'test-image' in docker_cmd
        assert 'bash' in docker_cmd
    
    @patch('claude_container.core.container_runner.DockerService')
    def test_run_command_no_command(self, mock_docker_service_class, temp_project_dir):
        """Test running command with no arguments (interactive shell)."""
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = True
        mock_docker_service_class.return_value = mock_docker
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        with patch.object(runner, '_run_interactive_container') as mock_interactive:
            runner.run_command([])
            mock_interactive.assert_called_once_with(['/bin/bash'])
    
    @patch('claude_container.core.container_runner.DockerService')
    def test_run_command_claude_interactive(self, mock_docker_service_class, temp_project_dir):
        """Test running interactive claude command."""
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = True
        mock_docker_service_class.return_value = mock_docker
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        with patch.object(runner, '_run_interactive_container') as mock_interactive:
            runner.run_command(['claude'])
            mock_interactive.assert_called_once_with(['claude'])
    
    @patch('claude_container.core.container_runner.DockerService')
    def test_run_command_claude_non_interactive_success(self, mock_docker_service_class, temp_project_dir, capsys):
        """Test running non-interactive claude command successfully."""
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = True
        
        # Mock container
        mock_container = MagicMock()
        mock_container.wait.return_value = {'StatusCode': 0}
        mock_container.logs.return_value = b"Task completed successfully"
        mock_docker.run_container.return_value = mock_container
        
        mock_docker_service_class.return_value = mock_docker
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        runner.run_command(['claude', 'code', 'task', 'start'])
        
        captured = capsys.readouterr()
        assert "Task completed successfully" in captured.out
        mock_container.remove.assert_called_once()
    
    @patch('claude_container.core.container_runner.DockerService')
    def test_run_command_claude_non_interactive_failure(self, mock_docker_service_class, temp_project_dir, capsys):
        """Test running non-interactive claude command that fails."""
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = True
        
        # Mock container
        mock_container = MagicMock()
        mock_container.wait.return_value = {'StatusCode': 1}
        mock_container.logs.return_value = b"Error: Task failed"
        mock_docker.run_container.return_value = mock_container
        
        mock_docker_service_class.return_value = mock_docker
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        runner.run_command(['claude', 'code', 'task', 'start'])
        
        captured = capsys.readouterr()
        assert "Error: Command 'claude code task start' failed with exit code 1" in captured.out
        assert "Error: Task failed" in captured.out
        mock_container.remove.assert_called_once()
    
    @patch('claude_container.core.container_runner.DockerService')
    def test_run_command_shell_syntax(self, mock_docker_service_class, temp_project_dir):
        """Test running command with shell syntax."""
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = True
        mock_docker.run_container.return_value = b"file1.txt file2.txt"
        mock_docker_service_class.return_value = mock_docker
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        runner.run_command(['ls *.txt'])
        
        # Verify shell was used
        call_kwargs = mock_docker.run_container.call_args[1]
        assert call_kwargs['command'] == ['/bin/sh', '-c', 'ls *.txt']
    
    @patch('claude_container.core.container_runner.DockerService')
    def test_run_command_container_error(self, mock_docker_service_class, temp_project_dir, capsys):
        """Test handling container errors."""
        mock_docker = MagicMock()
        mock_docker.image_exists.return_value = True
        
        # Import the exception
        from claude_container.services.exceptions import DockerServiceError
        
        # Create a mock error
        error = DockerServiceError("Container exited with error: Command not found")
        
        mock_docker.run_container.side_effect = error
        mock_docker_service_class.return_value = mock_docker
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        runner.run_command(['nonexistent'])
        
        captured = capsys.readouterr()
        # The error message from DockerServiceError
        assert "Error running command 'nonexistent': Container exited with error: Command not found" in captured.out
    
    def test_attach_and_cleanup(self, temp_project_dir, capsys):
        """Test attaching to container and cleanup."""
        mock_container = MagicMock()
        mock_container.attach.return_value = [b"line1\n", b"line2\n"]
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        runner._attach_and_cleanup(mock_container)
        
        captured = capsys.readouterr()
        assert "line1\n" in captured.out
        assert "line2\n" in captured.out
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()
    
    def test_attach_and_cleanup_keyboard_interrupt(self, temp_project_dir):
        """Test cleanup on keyboard interrupt."""
        mock_container = MagicMock()
        mock_container.attach.side_effect = KeyboardInterrupt()
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        runner._attach_and_cleanup(mock_container)
        
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()
    
    @patch('claude_container.core.container_runner.DockerService')
    def test_create_persistent_container_failure(self, mock_docker_service_class, temp_project_dir):
        """Test handling failure when creating persistent container."""
        mock_docker = MagicMock()
        mock_docker.run_container.side_effect = Exception("Docker error")
        mock_docker_service_class.return_value = mock_docker
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        with pytest.raises(RuntimeError, match="Failed to create container"):
            runner.create_persistent_container("task")
    
    @patch('claude_container.core.container_runner.DockerService')
    def test_write_file_success(self, mock_docker_service_class, temp_project_dir):
        """Test successfully writing a file to container."""
        mock_docker = MagicMock()
        mock_result = {'ExitCode': 0, 'stderr': b''}
        mock_docker.exec_in_container.return_value = mock_result
        mock_docker_service_class.return_value = mock_docker
        
        mock_container = MagicMock()
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        # Test simple content
        runner.write_file(mock_container, "/test/file.txt", "Hello World")
        
        # Verify exec was called
        mock_docker.exec_in_container.assert_called_once_with(
            mock_container,
            "sh -c 'cat > /test/file.txt << '''EOF'''\nHello World\nEOF'",
            stream=False,
            tty=False
        )
    
    @patch('claude_container.core.container_runner.DockerService')
    def test_write_file_with_quotes(self, mock_docker_service_class, temp_project_dir):
        """Test writing file content with quotes."""
        mock_docker = MagicMock()
        mock_result = {'ExitCode': 0, 'stderr': b''}
        mock_docker.exec_in_container.return_value = mock_result
        mock_docker_service_class.return_value = mock_docker
        
        mock_container = MagicMock()
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        # Test content with quotes
        content = "This has 'single quotes' in it"
        runner.write_file(mock_container, "/test/file.txt", content)
        
        # Verify quotes were escaped properly
        expected_content = "This has '\"'\"'single quotes'\"'\"' in it"
        mock_docker.exec_in_container.assert_called_once_with(
            mock_container,
            f"sh -c 'cat > /test/file.txt << '''EOF'''\n{expected_content}\nEOF'",
            stream=False,
            tty=False
        )
    
    @patch('claude_container.core.container_runner.DockerService')
    def test_write_file_failure(self, mock_docker_service_class, temp_project_dir):
        """Test handling write file failure."""
        mock_docker = MagicMock()
        mock_result = {'ExitCode': 1, 'stderr': b'Permission denied'}
        mock_docker.exec_in_container.return_value = mock_result
        mock_docker_service_class.return_value = mock_docker
        
        mock_container = MagicMock()
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        with pytest.raises(RuntimeError, match="Failed to write file: Permission denied"):
            runner.write_file(mock_container, "/test/file.txt", "Hello")
    
    @patch('claude_container.core.container_runner.DockerService')
    def test_write_file_exception(self, mock_docker_service_class, temp_project_dir):
        """Test handling exception during file write."""
        mock_docker = MagicMock()
        mock_docker.exec_in_container.side_effect = Exception("Docker error")
        mock_docker_service_class.return_value = mock_docker
        
        mock_container = MagicMock()
        
        data_dir = temp_project_dir / ".claude-container"
        runner = ContainerRunner(temp_project_dir, data_dir, "test-image")
        
        with pytest.raises(RuntimeError, match="Failed to write file /test/file.txt: Docker error"):
            runner.write_file(mock_container, "/test/file.txt", "Hello")