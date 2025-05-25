"""Smoke tests for the task daemon."""
import os
import json
import tempfile
from unittest.mock import patch, MagicMock, mock_open
import pytest

from claude_container.core.task_daemon import TaskDaemon, ClaudeTask


class TestTaskDaemon:
    """Smoke test suite for TaskDaemon."""
    
    @pytest.fixture
    def daemon(self):
        """Create a TaskDaemon instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            daemon = TaskDaemon()
            daemon.tasks_dir = tmpdir
            yield daemon
    
    def test_task_daemon_initialization(self, daemon):
        """Test that TaskDaemon initializes correctly."""
        assert daemon.socket_path is not None
        assert daemon.tasks == {}
        assert daemon.running == True
        assert daemon.max_concurrent_tasks == 3
    
    def test_claude_task_initialization(self):
        """Test ClaudeTask initialization."""
        task = ClaudeTask(
            task_id='test-123',
            command=['claude-code', '-p', 'test'],
            working_dir='/test/dir',
            branch_name='feature-branch',
            pr_url='https://github.com/user/repo/pull/1',
            metadata={'type': 'feature_task'}
        )
        
        assert task.task_id == 'test-123'
        assert task.command == ['claude-code', '-p', 'test']
        assert task.working_dir == '/test/dir'
        assert task.branch_name == 'feature-branch'
        assert task.pr_url == 'https://github.com/user/repo/pull/1'
        assert task.metadata['type'] == 'feature_task'
        assert task.status == 'pending'
        assert task.process is None
    
    def test_submit_feature_task_request(self, daemon):
        """Test submitting a feature task request."""
        request = {
            'action': 'submit',
            'command': ['claude-code', '--dangerously-skip-permissions', '-p', 'test prompt'],
            'working_dir': '/test/dir',
            'metadata': {
                'branch': 'feature-branch',
                'task_description': 'Add new feature',
                'type': 'feature_task'
            }
        }
        
        response = daemon._process_request(request)
        
        assert 'task_id' in response
        assert response['status'] == 'queued'
        assert response['branch'] == 'feature-branch'
        
        # Verify task was created
        task_id = response['task_id']
        assert task_id in daemon.tasks
        task = daemon.tasks[task_id]
        assert task.metadata['type'] == 'feature_task'
    
    
    def test_list_tasks_request(self, daemon):
        """Test listing tasks."""
        # Add some tasks
        task1 = ClaudeTask('task-1', ['cmd1'], '/dir1', 'branch-1', 'https://pr1', {})
        task1.status = 'running'
        
        task2 = ClaudeTask('task-2', ['cmd2'], '/dir2', 'branch-2', None, {})
        task2.status = 'completed'
        task2.exit_code = 0
        
        daemon.tasks = {'task-1': task1, 'task-2': task2}
        
        request = {'action': 'list'}
        response = daemon._process_request(request)
        
        assert 'tasks' in response
        assert len(response['tasks']) == 2
    
    def test_unknown_action_request(self, daemon):
        """Test handling of unknown action."""
        request = {'action': 'unknown_action'}
        response = daemon._process_request(request)
        
        assert 'error' in response
        assert 'Unknown action' in response['error']
    
    def test_get_output_request(self, daemon):
        """Test getting task output when no output exists."""
        task = ClaudeTask('task-123', ['cmd'], '/dir', 'branch', None, {})
        daemon.tasks['task-123'] = task
        
        request = {'action': 'output', 'task_id': 'task-123'}
        response = daemon._process_request(request)
        
        # Should return empty output or error
        assert 'task_id' in response or 'error' in response