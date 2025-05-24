"""Task daemon for managing Claude Code processes."""

import asyncio
import json
import socket
import os
import subprocess
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import threading
import queue


class ClaudeTask:
    """Represents a Claude Code task."""
    
    def __init__(self, task_id: str, command: List[str], working_dir: str = "/workspace"):
        self.task_id = task_id
        self.command = command
        self.working_dir = working_dir
        self.status = "pending"
        self.process: Optional[subprocess.Popen] = None
        self.output = []
        self.error = []
        self.started_at = None
        self.completed_at = None
        self.exit_code = None


class TaskDaemon:
    """Daemon that manages Claude Code tasks."""
    
    def __init__(self, socket_path: str = None):
        if socket_path is None:
            from pathlib import Path
            socket_path = str(Path.home() / ".claude-daemon.sock")
        self.socket_path = socket_path
        self.tasks: Dict[str, ClaudeTask] = {}
        self.running = True
        self.task_queue = queue.Queue()
        self.max_concurrent_tasks = 3
        
    def start(self):
        """Start the daemon."""
        # Remove existing socket
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        
        # Create socket
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(self.socket_path)
        self.socket.listen(5)
        
        print(f"Task daemon listening on {self.socket_path}")
        
        # Start worker threads
        for i in range(self.max_concurrent_tasks):
            worker = threading.Thread(target=self._task_worker, daemon=True)
            worker.start()
        
        # Accept connections
        while self.running:
            try:
                conn, _ = self.socket.accept()
                threading.Thread(target=self._handle_connection, args=(conn,), daemon=True).start()
            except KeyboardInterrupt:
                break
        
        self.shutdown()
    
    def _handle_connection(self, conn):
        """Handle a client connection."""
        try:
            data = conn.recv(4096).decode('utf-8')
            request = json.loads(data)
            
            response = self._process_request(request)
            conn.send(json.dumps(response).encode('utf-8'))
        except Exception as e:
            error_response = {"error": str(e)}
            conn.send(json.dumps(error_response).encode('utf-8'))
        finally:
            conn.close()
    
    def _process_request(self, request):
        """Process a request from client."""
        action = request.get('action')
        
        if action == 'submit':
            # Submit a new task
            command = request.get('command', [])
            working_dir = request.get('working_dir', '.')
            task_id = str(uuid.uuid4())
            task = ClaudeTask(task_id, command, working_dir)
            self.tasks[task_id] = task
            self.task_queue.put(task)
            
            return {
                "task_id": task_id,
                "status": "queued"
            }
        
        elif action == 'status':
            # Get task status
            task_id = request.get('task_id')
            task = self.tasks.get(task_id)
            
            if not task:
                return {"error": "Task not found"}
            
            return {
                "task_id": task_id,
                "status": task.status,
                "exit_code": task.exit_code,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None
            }
        
        elif action == 'output':
            # Get task output
            task_id = request.get('task_id')
            task = self.tasks.get(task_id)
            
            if not task:
                return {"error": "Task not found"}
            
            return {
                "task_id": task_id,
                "output": '\n'.join(task.output),
                "error": '\n'.join(task.error)
            }
        
        elif action == 'list':
            # List all tasks
            tasks_info = []
            for task_id, task in self.tasks.items():
                tasks_info.append({
                    "task_id": task_id,
                    "status": task.status,
                    "command": ' '.join(task.command)
                })
            return {"tasks": tasks_info}
        
        elif action == 'kill':
            # Kill a running task
            task_id = request.get('task_id')
            task = self.tasks.get(task_id)
            
            if not task:
                return {"error": "Task not found"}
            
            if task.process and task.status == "running":
                task.process.terminate()
                task.status = "killed"
                return {"status": "killed"}
            
            return {"error": "Task not running"}
        
        else:
            return {"error": f"Unknown action: {action}"}
    
    def _task_worker(self):
        """Worker thread that executes tasks."""
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                self._execute_task(task)
            except queue.Empty:
                continue
    
    def _execute_task(self, task: ClaudeTask):
        """Execute a Claude Code task in a Docker container."""
        import docker
        from pathlib import Path
        
        task.status = "running"
        task.started_at = datetime.now()
        
        # Add --dangerously-skip-permissions for Claude commands
        command = task.command.copy()
        if command and command[0] == 'claude' and '--dangerously-skip-permissions' not in command:
            command.insert(1, '--dangerously-skip-permissions')
        
        try:
            # Connect to Docker
            client = docker.from_env()
            
            # Determine container image based on working directory
            project_path = Path(task.working_dir).resolve()
            project_name = project_path.name
            image_name = f"claude-container-{project_name}".lower()
            
            # Check if image exists
            try:
                client.images.get(image_name)
            except docker.errors.ImageNotFound:
                task.status = "error"
                task.error.append(f"Docker image '{image_name}' not found. Run 'claude-container build' first.")
                task.exit_code = -1
                return
            
            # Prepare volumes
            volumes = {
                str(project_path): {'bind': '/workspace', 'mode': 'rw'},
            }
            
            # Mount Claude configuration to node user's home
            claude_config = Path.home() / '.claude.json'
            if claude_config.exists():
                volumes[str(claude_config)] = {'bind': '/home/node/.claude.json', 'mode': 'rw'}
            
            claude_dir = Path.home() / '.claude'
            if claude_dir.exists():
                volumes[str(claude_dir)] = {'bind': '/home/node/.claude', 'mode': 'rw'}
            
            # Run container
            container = client.containers.run(
                image_name,
                ' '.join(command),
                volumes=volumes,
                working_dir='/workspace',
                detach=True,
                name=f"claude-task-{task.task_id[:8]}",
                environment={
                    'CLAUDE_TASK_ID': task.task_id,
                    'CLAUDE_CONFIG_DIR': '/home/node/.claude'
                }
            )
            
            # Stream logs
            for line in container.logs(stream=True, follow=True):
                task.output.append(line.decode('utf-8').rstrip())
            
            # Get exit code
            container.reload()
            task.exit_code = container.attrs['State']['ExitCode']
            
            task.status = "completed" if task.exit_code == 0 else "failed"
            
            # Clean up container
            container.remove()
            
        except Exception as e:
            task.status = "error"
            task.error.append(f"Error: {type(e).__name__}: {str(e)}")
            task.exit_code = -1
            import traceback
            task.error.append(traceback.format_exc())
        
        finally:
            task.completed_at = datetime.now()
            task.process = None
    
    def shutdown(self):
        """Shutdown the daemon."""
        self.running = False
        if hasattr(self, 'socket'):
            self.socket.close()
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)


if __name__ == "__main__":
    daemon = TaskDaemon()
    daemon.start()