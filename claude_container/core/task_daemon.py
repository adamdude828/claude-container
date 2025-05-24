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
from .github_integration import GitHubIntegration
from .wrapper_scripts import get_claude_wrapper_script, get_git_config_script


class ClaudeTask:
    """Represents a Claude Code task."""
    
    def __init__(self, task_id: str, command: List[str], working_dir: str = "/workspace", 
                 branch_name: Optional[str] = None, pr_url: Optional[str] = None):
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
        self.branch_name = branch_name
        self.pr_url = pr_url


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
        
    def validate_github_cli(self):
        """Check if gh CLI is installed and authenticated."""
        try:
            result = subprocess.run(['gh', 'auth', 'status'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(
                    "GitHub CLI (gh) is required and must be authenticated.\n"
                    "Install: https://cli.github.com/\n"
                    "Authenticate: gh auth login"
                )
        except FileNotFoundError:
            raise RuntimeError(
                "GitHub CLI (gh) is not installed.\n"
                "Install: https://cli.github.com/"
            )
        
    def start(self):
        """Start the daemon."""
        # Validate GitHub CLI first
        try:
            self.validate_github_cli()
            print("✓ GitHub CLI authenticated")
        except RuntimeError as e:
            print(f"✗ {e}")
            return
        
        # Remove existing socket
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        
        # Create socket
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(self.socket_path)
        self.socket.listen(5)
        
        print(f"✓ Task daemon listening on {self.socket_path}")
        
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
            task_id = str(uuid.uuid4())[:8]
            
            # Create branch and PR for the task
            github = GitHubIntegration(working_dir)
            
            # Extract task description for logging
            task_description = command[1] if len(command) > 1 and command[0] == 'claude' else ' '.join(command)
            
            # Check git status first
            is_clean, status_output = github.check_git_status()
            if not is_clean:
                # Create a failed task record so user can check logs
                task = ClaudeTask(task_id, command, working_dir, None, None)
                task.status = "failed"
                task.error.append("Git working directory is not clean. Please commit or stash changes first.")
                task.error.append(status_output)
                self.tasks[task_id] = task
                
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "error": "Git working directory is not clean. Please commit or stash changes first."
                }
            
            # Create branch
            branch_name = f"claude-task-{task_id}"
            if not github.create_branch(branch_name):
                # Create a failed task record
                task = ClaudeTask(task_id, command, working_dir, branch_name, None)
                task.status = "failed"
                task.error.append(f"Failed to create branch {branch_name}")
                self.tasks[task_id] = task
                
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "error": f"Failed to create branch {branch_name}"
                }
            
            # Create PR with task description
            pr_title = f"Claude Task: {task_description[:50]}{'...' if len(task_description) > 50 else ''}"
            pr_body = f"Task ID: {task_id}\nTask: {task_description}\n\nIn progress..."
            pr_url = github.create_pull_request(branch_name, pr_title, pr_body)
            
            if not pr_url:
                # Create a failed task record
                task = ClaudeTask(task_id, command, working_dir, branch_name, None)
                task.status = "failed"
                task.error.append(f"Failed to create PR for branch {branch_name}")
                self.tasks[task_id] = task
                
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "error": f"Failed to create PR for branch {branch_name}",
                    "branch": branch_name
                }
            
            # Create task with branch and PR info
            task = ClaudeTask(task_id, command, working_dir, branch_name, pr_url)
            self.tasks[task_id] = task
            self.task_queue.put(task)
            
            return {
                "task_id": task_id,
                "status": "queued",
                "branch": branch_name,
                "pr_url": pr_url
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
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "branch": task.branch_name,
                "pr_url": task.pr_url
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
                    "command": task.command
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
        
        # Prepare command with wrapper script if branch is set
        if task.branch_name:
            # Add --dangerously-skip-permissions for Claude commands
            command = task.command.copy()
            if command and command[0] == 'claude' and '--dangerously-skip-permissions' not in command:
                command.insert(1, '--dangerously-skip-permissions')
            
            # Get wrapper scripts
            wrapper_script = get_claude_wrapper_script()
            git_config_script = get_git_config_script()
            
            # Create the full command that sets up scripts and runs them
            full_command = [
                '/bin/bash', '-c',
                f'''
# Write git config script
cat > /tmp/git-config.sh << 'EOF'
{git_config_script}
EOF

# Write wrapper script  
cat > /tmp/claude-wrapper.sh << 'EOF'
{wrapper_script}
EOF

# Make scripts executable
chmod +x /tmp/git-config.sh /tmp/claude-wrapper.sh

# Configure git
/tmp/git-config.sh

# Run wrapper with branch and command
/tmp/claude-wrapper.sh {task.branch_name} {' '.join(command)}
'''
            ]
            command = full_command
        else:
            # Normal execution without git operations
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
            
            # Mount SSH keys for git operations if branch is set
            if task.branch_name:
                ssh_dir = Path.home() / '.ssh'
                if ssh_dir.exists():
                    volumes[str(ssh_dir)] = {'bind': '/home/node/.ssh', 'mode': 'ro'}
                
                # Mount git config
                gitconfig = Path.home() / '.gitconfig'
                if gitconfig.exists():
                    volumes[str(gitconfig)] = {'bind': '/home/node/.gitconfig', 'mode': 'ro'}
            
            # Run container
            container = client.containers.run(
                image_name,
                command if isinstance(command, list) else ' '.join(command),
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
            task.completed_at = datetime.now()
            
            # Update PR status if we have a PR
            if task.pr_url and task.branch_name:
                github = GitHubIntegration(task.working_dir)
                pr_number = github.get_pr_number_from_url(task.pr_url)
                
                if pr_number:
                    # Update PR description with final status
                    status_emoji = "✅" if task.exit_code == 0 else "❌"
                    updated_body = f"""Task ID: {task.task_id}
Command: {' '.join(task.command)}

Status: {status_emoji} {task.status.upper()}
Exit Code: {task.exit_code}
Started: {task.started_at.isoformat()}
Completed: {task.completed_at.isoformat() if task.completed_at else 'N/A'}

---
This PR was automatically created by Claude Container.
"""
                    github.update_pr_description(pr_number, updated_body)
                    
                    # Mark PR as ready if task succeeded
                    if task.exit_code == 0:
                        github.mark_pr_ready(pr_number)
            
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