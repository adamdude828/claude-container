"""Unit tests for CLI helper functions."""

import sys
import tempfile
from pathlib import Path
from datetime import datetime
from unittest import mock

import pytest
import click
from click.testing import CliRunner

from claude_container.cli.helpers import (
    ensure_authenticated,
    get_project_context,
    ensure_container_built,
    get_storage_and_runner,
    get_docker_client,
    get_config_manager,
    resolve_task_id,
    format_pr_display,
    format_task_table,
    print_table,
    open_in_editor,
    cleanup_container,
)
from claude_container.core.constants import DATA_DIR_NAME
from claude_container.models.task import TaskStatus, TaskMetadata
from claude_container.models.config import ContainerConfig


class TestEnsureAuthenticated:
    """Test ensure_authenticated function."""
    
    @mock.patch('claude_container.cli.commands.auth_check.check_claude_auth')
    def test_authenticated_succeeds(self, mock_check_auth):
        """Test that authenticated user passes."""
        mock_check_auth.return_value = True
        # Should not raise or exit
        ensure_authenticated()
        mock_check_auth.assert_called_once()
    
    @mock.patch('claude_container.cli.commands.auth_check.check_claude_auth')
    def test_unauthenticated_exits(self, mock_check_auth):
        """Test that unauthenticated user exits."""
        mock_check_auth.return_value = False
        with pytest.raises(SystemExit) as excinfo:
            ensure_authenticated()
        assert excinfo.value.code == 1
        mock_check_auth.assert_called_once()


class TestGetProjectContext:
    """Test get_project_context function."""
    
    def test_returns_current_directory_and_data_dir(self):
        """Test that it returns cwd and data directory."""
        project_root, data_dir = get_project_context()
        assert project_root == Path.cwd()
        assert data_dir == project_root / DATA_DIR_NAME
    
    @mock.patch('claude_container.cli.helpers.Path.cwd')
    def test_uses_custom_working_directory(self, mock_cwd):
        """Test with mocked working directory."""
        test_path = Path("/test/project")
        mock_cwd.return_value = test_path
        
        project_root, data_dir = get_project_context()
        assert project_root == test_path
        assert data_dir == test_path / DATA_DIR_NAME


class TestEnsureContainerBuilt:
    """Test ensure_container_built function."""
    
    def test_exits_if_data_dir_missing(self, tmp_path):
        """Test that it exits if data directory doesn't exist."""
        data_dir = tmp_path / "nonexistent"
        
        runner = CliRunner()
        with pytest.raises(SystemExit) as excinfo:
            ensure_container_built(data_dir)
        assert excinfo.value.code == 1
    
    def test_succeeds_if_data_dir_exists(self, tmp_path):
        """Test that it succeeds if data directory exists."""
        data_dir = tmp_path / DATA_DIR_NAME
        data_dir.mkdir()
        
        # Should not raise
        ensure_container_built(data_dir)


class TestGetStorageAndRunner:
    """Test get_storage_and_runner function."""
    
    @mock.patch('claude_container.cli.helpers.ContainerRunner')
    @mock.patch('claude_container.cli.helpers.TaskStorageManager')
    @mock.patch('claude_container.cli.helpers.get_project_context')
    def test_success_case(self, mock_context, mock_storage_cls, mock_runner_cls, tmp_path):
        """Test successful initialization."""
        # Setup mocks
        project_root = tmp_path / "project"
        data_dir = project_root / DATA_DIR_NAME
        data_dir.mkdir(parents=True)
        
        mock_context.return_value = (project_root, data_dir)
        mock_storage = mock.Mock()
        mock_storage_cls.return_value = mock_storage
        
        mock_runner = mock.Mock()
        mock_runner.docker_client.image_exists.return_value = True
        mock_runner_cls.return_value = mock_runner
        
        # Call function
        storage, runner = get_storage_and_runner()
        
        # Verify
        assert storage == mock_storage
        assert runner == mock_runner
        mock_storage_cls.assert_called_once_with(data_dir)
        mock_runner_cls.assert_called_once()
    
    @mock.patch('claude_container.cli.helpers.get_project_context')
    def test_exits_if_container_not_built(self, mock_context, tmp_path):
        """Test that it exits if container not built."""
        project_root = tmp_path / "project"
        data_dir = project_root / "nonexistent"
        
        mock_context.return_value = (project_root, data_dir)
        
        with pytest.raises(SystemExit) as excinfo:
            get_storage_and_runner()
        assert excinfo.value.code == 1


class TestGetDockerClient:
    """Test get_docker_client function."""
    
    @mock.patch('claude_container.cli.helpers.DockerClient')
    def test_success_case(self, mock_docker_cls):
        """Test successful Docker client creation."""
        mock_client = mock.Mock()
        mock_docker_cls.return_value = mock_client
        
        client = get_docker_client()
        assert client == mock_client
        mock_docker_cls.assert_called_once()
    
    @mock.patch('claude_container.cli.helpers.DockerClient')
    def test_exits_on_error(self, mock_docker_cls):
        """Test that it exits on Docker error."""
        mock_docker_cls.side_effect = RuntimeError("Docker not found")
        
        with pytest.raises(SystemExit) as excinfo:
            get_docker_client()
        assert excinfo.value.code == 1


class TestGetConfigManager:
    """Test get_config_manager function."""
    
    @mock.patch('claude_container.cli.helpers.ConfigManager')
    @mock.patch('claude_container.cli.helpers.get_project_context')
    def test_returns_existing_config(self, mock_context, mock_config_cls, tmp_path):
        """Test that it returns existing config."""
        # Setup
        project_root = tmp_path / "project"
        data_dir = project_root / DATA_DIR_NAME
        data_dir.mkdir(parents=True)
        mock_context.return_value = (project_root, data_dir)
        
        mock_manager = mock.Mock()
        mock_config = ContainerConfig(type="cached", generated_at="2024-01-01")
        mock_manager.get_container_config.return_value = mock_config
        mock_config_cls.return_value = mock_manager
        
        # Call
        manager, config = get_config_manager()
        
        # Verify
        assert manager == mock_manager
        assert config == mock_config
        mock_manager.save_container_config.assert_not_called()
    
    @mock.patch('claude_container.cli.helpers.ConfigManager')
    @mock.patch('claude_container.cli.helpers.get_project_context')
    def test_creates_new_config(self, mock_context, mock_config_cls, tmp_path):
        """Test that it creates new config if none exists."""
        # Setup
        project_root = tmp_path / "project"
        data_dir = project_root / DATA_DIR_NAME
        data_dir.mkdir(parents=True)
        mock_context.return_value = (project_root, data_dir)
        
        mock_manager = mock.Mock()
        mock_manager.get_container_config.return_value = None
        mock_config_cls.return_value = mock_manager
        
        # Call
        manager, config = get_config_manager()
        
        # Verify
        assert manager == mock_manager
        assert config.type == "cached"
        assert config.generated_at
        mock_manager.save_container_config.assert_called_once_with(config)


class TestResolveTaskId:
    """Test resolve_task_id function."""
    
    def test_returns_exact_match(self):
        """Test that it returns exact ID match."""
        mock_storage = mock.Mock()
        task = TaskMetadata(
            id="task-123",
            description="Test task",
            status=TaskStatus.CREATED,
            created_at=datetime.now(),
            branch_name="feature/test"
        )
        mock_storage.get_task.return_value = task
        
        result = resolve_task_id(mock_storage, "task-123")
        assert result == task
        mock_storage.get_task.assert_called_once_with("task-123")
    
    def test_returns_short_id_match(self):
        """Test that it matches short IDs."""
        mock_storage = mock.Mock()
        task = TaskMetadata(
            id="task-123-full",
            description="Test task",
            status=TaskStatus.CREATED,
            created_at=datetime.now(),
            branch_name="feature/test"
        )
        mock_storage.get_task.return_value = None
        mock_storage.list_tasks.return_value = [task]
        
        result = resolve_task_id(mock_storage, "task-123")
        assert result == task
    
    def test_exits_on_multiple_matches(self):
        """Test that it exits when multiple tasks match."""
        mock_storage = mock.Mock()
        task1 = TaskMetadata(
            id="task-123-one",
            description="Test task 1",
            status=TaskStatus.CREATED,
            created_at=datetime.now(),
            branch_name="feature/test1"
        )
        task2 = TaskMetadata(
            id="task-123-two",
            description="Test task 2",
            status=TaskStatus.CREATED,
            created_at=datetime.now(),
            branch_name="feature/test2"
        )
        mock_storage.get_task.return_value = None
        mock_storage.list_tasks.return_value = [task1, task2]
        
        with pytest.raises(SystemExit) as excinfo:
            resolve_task_id(mock_storage, "task-123")
        assert excinfo.value.code == 1
    
    def test_exits_on_no_match(self):
        """Test that it exits when no task matches."""
        mock_storage = mock.Mock()
        mock_storage.get_task.return_value = None
        mock_storage.list_tasks.return_value = []
        
        with pytest.raises(SystemExit) as excinfo:
            resolve_task_id(mock_storage, "task-123")
        assert excinfo.value.code == 1


class TestFormatPrDisplay:
    """Test format_pr_display function."""
    
    def test_empty_pr_url(self):
        """Test with no PR URL."""
        assert format_pr_display(None) == ""
        assert format_pr_display("") == ""
    
    def test_standard_github_pr_url(self):
        """Test with standard GitHub PR URL."""
        url = "https://github.com/owner/repo/pull/123"
        result = format_pr_display(url)
        assert "PR #123" in result
    
    def test_non_standard_pr_url(self):
        """Test with non-standard PR URL."""
        url = "https://github.com/owner/repo/pr/123"
        result = format_pr_display(url)
        assert result == click.style("PR", fg='cyan')


class TestFormatTaskTable:
    """Test format_task_table function."""
    
    def test_empty_task_list(self):
        """Test with empty task list."""
        result = format_task_table([])
        assert "ID" in result
        assert "STATUS" in result
    
    def test_single_task(self):
        """Test with single task."""
        task = TaskMetadata(
            id="task-12345678",
            description="Test task description",
            status=TaskStatus.CREATED,
            created_at=datetime.now(),
            branch_name="feature/test"
        )
        
        result = format_task_table([task])
        assert "task-123" in result  # Short ID
        assert "CREATED" in result
        assert "feature/test" in result
        assert "Test task description" in result
    
    def test_long_description_truncation(self):
        """Test that long descriptions are truncated."""
        task = TaskMetadata(
            id="task-123",
            description="A" * 100,  # Long description
            status=TaskStatus.CREATED,
            created_at=datetime.now(),
            branch_name="feature/test"
        )
        
        result = format_task_table([task], max_desc_length=20)
        assert "A" * 17 + "..." in result
    
    def test_continuation_count(self):
        """Test that continuation count is displayed."""
        task = TaskMetadata(
            id="task-123",
            description="Test task",
            status=TaskStatus.CONTINUED,
            created_at=datetime.now(),
            branch_name="feature/test",
            continuation_count=3
        )
        
        result = format_task_table([task])
        assert "(cont: 3)" in result


class TestPrintTable:
    """Test print_table function."""
    
    def test_basic_table(self):
        """Test printing basic table."""
        runner = CliRunner()
        
        @click.command()
        def cmd():
            print_table(["Col1", "Col2"], [["A", "B"], ["C", "D"]])
        
        result = runner.invoke(cmd)
        assert result.exit_code == 0
        assert "Col1" in result.output
        assert "Col2" in result.output
        assert "A" in result.output
        assert "B" in result.output


class TestOpenInEditor:
    """Test open_in_editor function."""
    
    @mock.patch('subprocess.run')
    @mock.patch('os.environ.get')
    def test_successful_edit(self, mock_env_get, mock_run):
        """Test successful editor operation."""
        mock_env_get.return_value = 'vim'
        mock_run.return_value.returncode = 0
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            test_file = Path(f.name)
        
        # Mock the file read
        with mock.patch('builtins.open', mock.mock_open(read_data="Edited content")):
            result = open_in_editor("Initial content")
        
        assert result == "Edited content"
        mock_run.assert_called_once()
    
    @mock.patch('subprocess.run')
    @mock.patch('os.environ.get')
    def test_editor_failure(self, mock_env_get, mock_run):
        """Test editor failure returns empty string."""
        mock_env_get.return_value = 'vim'
        mock_run.return_value.returncode = 1
        
        result = open_in_editor("Initial content")
        assert result == ""
    
    @mock.patch('os.environ.get')
    def test_no_editor_configured(self, mock_env_get):
        """Test fallback when no editor configured."""
        # Return None for EDITOR to simulate no editor configured
        mock_env_get.side_effect = lambda key, default=None: default
        
        with mock.patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            with mock.patch('builtins.open', mock.mock_open(read_data="Content")):
                result = open_in_editor("Test")
        
        # Should use nano as fallback
        assert mock_run.call_args[0][0][0] == 'nano'


class TestCleanupContainer:
    """Test cleanup_container function."""
    
    def test_successful_cleanup(self):
        """Test successful container cleanup."""
        mock_container = mock.Mock()
        
        runner = CliRunner()
        
        @click.command()
        def cmd():
            cleanup_container(mock_container)
        
        result = runner.invoke(cmd)
        assert result.exit_code == 0
        assert "Cleaning up resources" in result.output
        assert "Container removed successfully" in result.output
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()
    
    def test_cleanup_with_error(self):
        """Test cleanup with container error."""
        mock_container = mock.Mock()
        mock_container.stop.side_effect = Exception("Stop failed")
        
        runner = CliRunner()
        
        @click.command()
        def cmd():
            cleanup_container(mock_container)
        
        result = runner.invoke(cmd)
        assert result.exit_code == 0
        assert "Warning: Failed to remove container" in result.output
    
    def test_cleanup_with_none_container(self):
        """Test cleanup with None container."""
        runner = CliRunner()
        
        @click.command()
        def cmd():
            cleanup_container(None)
        
        result = runner.invoke(cmd)
        assert result.exit_code == 0
        # Should not output anything for None container