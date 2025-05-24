import pytest
from click.testing import CliRunner
from unittest.mock import Mock, MagicMock
import tempfile
import os
from pathlib import Path


@pytest.fixture
def cli_runner():
    """Provides a Click CLI runner for testing commands."""
    return CliRunner()


@pytest.fixture
def mock_docker_client():
    """Provides a mocked Docker client."""
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.containers.list.return_value = []
    mock_client.images.list.return_value = []
    return mock_client


@pytest.fixture
def temp_project_dir():
    """Creates a temporary project directory with basic structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        
        # Create basic project structure
        (project_path / "src").mkdir()
        (project_path / "src" / "main.py").write_text("print('Hello, World!')")
        (project_path / "Dockerfile").write_text("FROM python:3.10\nCOPY . /app\nWORKDIR /app")
        (project_path / ".claude-container").mkdir()
        
        yield project_path


@pytest.fixture
def mock_config():
    """Provides a mock configuration object."""
    from claude_container.models.container import ContainerConfig
    
    return ContainerConfig(
        base_image="python:3.10",
        env_vars={},
        runtime_versions=[],
        custom_commands=[]
    )


@pytest.fixture
def mock_session():
    """Provides a mock session object."""
    from claude_container.models.session import Session, SessionStatus
    
    return Session(
        id="test-session-123",
        container_id="container-abc123",
        status=SessionStatus.RUNNING,
        command="python main.py",
        created_at="2024-01-01T00:00:00"
    )


@pytest.fixture(autouse=True)
def mock_claude_executable(monkeypatch):
    """Mock the Claude executable path for all tests."""
    monkeypatch.setenv("CLAUDE_EXECUTABLE", "/usr/local/bin/claude")
    return "/usr/local/bin/claude"


@pytest.fixture
def isolated_cli_runner(cli_runner):
    """Provides a CLI runner with isolated filesystem."""
    with cli_runner.isolated_filesystem():
        yield cli_runner