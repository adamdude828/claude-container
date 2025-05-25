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
import logging
import sys
import shlex
try:
    from .github_integration import GitHubIntegration
    from .wrapper_scripts import get_claude_wrapper_script, get_git_config_script
except ImportError:
    # When running as a script, use absolute imports
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from claude_container.core.github_integration import GitHubIntegration
    from claude_container.core.wrapper_scripts import get_claude_wrapper_script, get_git_config_script

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


class ClaudeTask:
    """Represents a Claude Code task."""
    
    def __init__(self, task_id: str, command: List[str], working_dir: str = "/workspace", 
                 branch_name: Optional[str] = None, pr_url: Optional[str] = None, 
                 metadata: Optional[Dict] = None):
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
        self.metadata = metadata or {}


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
                logger.warning(
                    "GitHub CLI (gh) is not authenticated. PR creation will be disabled.\n"
                    "To enable PR creation, run: gh auth login"
                )
                return False
            return True
        except FileNotFoundError:
            logger.warning(
                "GitHub CLI (gh) is not installed. PR creation will be disabled.\n"
                "To enable PR creation, install from: https://cli.github.com/"
            )
            return False
        
    def start(self):
        """Start the daemon."""
        logger.info("Starting Claude task daemon...")
        
        # Validate GitHub CLI (but don't fail if not available)
        self.github_available = self.validate_github_cli()
        if self.github_available:
            logger.info("✓ GitHub CLI authenticated")
        else:
            logger.info("✗ GitHub CLI not available - PR creation disabled")
        
        try:
            # Remove existing socket
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
                logger.info(f"Removed existing socket at {self.socket_path}")
            
            # Create socket
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.bind(self.socket_path)
            self.socket.listen(5)
            
            logger.info(f"✓ Task daemon listening on {self.socket_path}")
            
            # Start worker threads
            for i in range(self.max_concurrent_tasks):
                worker = threading.Thread(target=self._task_worker, daemon=True)
                worker.start()
                logger.info(f"Started worker thread {i+1}")
            
            logger.info("Daemon ready to accept connections")
            
            # Accept connections
            while self.running:
                try:
                    self.socket.settimeout(1.0)  # Add timeout to allow checking self.running
                    try:
                        conn, _ = self.socket.accept()
                        logger.debug("Accepted new connection")
                        threading.Thread(target=self._handle_connection, args=(conn,), daemon=True).start()
                    except socket.timeout:
                        continue
                except KeyboardInterrupt:
                    logger.info("Received keyboard interrupt")
                    break
                except Exception as e:
                    logger.error(f"Error accepting connection: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Fatal error starting daemon: {e}")
            raise
        finally:
            self.shutdown()
    
    def _handle_connection(self, conn):
        """Handle a client connection."""
        try:
            logger.debug("Handling new connection")
            data = conn.recv(4096).decode('utf-8')
            logger.debug(f"Received raw data: {len(data)} bytes")
            logger.debug(f"Raw data preview: {data[:200]}..." if len(data) > 200 else f"Raw data: {data}")
            
            request = json.loads(data)
            logger.debug(f"Parsed request successfully: action={request.get('action')}")
            
            response = self._process_request(request)
            logger.debug(f"Generated response: {response}")
            
            response_data = json.dumps(response).encode('utf-8')
            logger.debug(f"Sending response: {len(response_data)} bytes")
            conn.send(response_data)
            logger.debug("Response sent successfully")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON request: {e}")
            logger.error(f"Raw data: {data}")
            error_response = {"error": f"Invalid JSON: {str(e)}"}
            conn.send(json.dumps(error_response).encode('utf-8'))
        except Exception as e:
            logger.error(f"Error handling connection: {type(e).__name__}: {e}", exc_info=True)
            error_response = {"error": str(e)}
            try:
                conn.send(json.dumps(error_response).encode('utf-8'))
            except:
                logger.error("Failed to send error response")
        finally:
            conn.close()
            logger.debug("Connection closed")
    
    def _process_request(self, request):
        """Process a request from client."""
        action = request.get('action')
        logger.debug(f"Processing request with action: {action}")
        
        if action == 'submit':
            # Submit a new task
            command = request.get('command', [])
            working_dir = request.get('working_dir', '.')
            metadata = request.get('metadata', {})
            task_id = str(uuid.uuid4())[:8]
            
            logger.info(f"Processing submit request: task_id={task_id}")
            logger.debug(f"Command: {command}")
            logger.debug(f"Working dir: {working_dir}")
            logger.debug(f"Metadata: {metadata}")
            
            # Check if this is a feature task (created by task start command)
            is_feature_task = metadata.get('type') == 'feature_task'
            logger.debug(f"Is feature task: {is_feature_task}")
            
            if is_feature_task:
                # For feature tasks, branch is already created by the CLI
                branch_name = metadata.get('branch')
                task_description = metadata.get('task_description', '')
                
                logger.info(f"Creating feature task: branch={branch_name}, description={task_description[:50]}...")
                
                # Create task without PR (will be created after completion)
                task = ClaudeTask(task_id, command, working_dir, branch_name, None, metadata)
                self.tasks[task_id] = task
                self.task_queue.put(task)
                
                logger.info(f"Feature task {task_id} queued successfully")
                
                return {
                    "task_id": task_id,
                    "status": "queued",
                    "branch": branch_name
                }
            else:
                # Original behavior for non-feature tasks
                # Create branch and PR for the task
                github = GitHubIntegration(working_dir)
                
                # Extract task description for logging
                task_description = command[1] if len(command) > 1 and command[0] == 'claude' else ' '.join(command)
                
                # Check git status first
                is_clean, status_output = github.check_git_status()
                if not is_clean:
                    # Create a failed task record so user can check logs
                    task = ClaudeTask(task_id, command, working_dir, None, None, metadata)
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
                    task = ClaudeTask(task_id, command, working_dir, branch_name, None, metadata)
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
                    task = ClaudeTask(task_id, command, working_dir, branch_name, None, metadata)
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
                task = ClaudeTask(task_id, command, working_dir, branch_name, pr_url, metadata)
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
    
    def _find_git_root(self, path: str) -> Optional[Path]:
        """Find the git repository root by walking up the directory tree."""
        current = Path(path).resolve()
        
        while current != current.parent:
            if (current / '.git').exists():
                return current
            current = current.parent
        
        return None
    
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
            
            # Get wrapper script
            wrapper_script = get_claude_wrapper_script()
            
            # Create the full command that sets up scripts and runs them
            full_command = [
                '/bin/bash', '-c',
                f'''
# Write wrapper script  
cat > /tmp/claude-wrapper.sh << 'EOF'
{wrapper_script}
EOF

# Make script executable
chmod +x /tmp/claude-wrapper.sh

# Run wrapper with branch and command
/tmp/claude-wrapper.sh {task.branch_name} {' '.join(shlex.quote(arg) for arg in command)}
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
            
            # Find git root and prepare volumes
            git_root = self._find_git_root(task.working_dir)
            if git_root:
                # Mount the git root as workspace
                volumes = {
                    str(git_root): {'bind': '/workspace', 'mode': 'rw'},
                }
                # Calculate relative path from git root to working directory
                relative_path = project_path.relative_to(git_root)
                container_working_dir = f'/workspace/{relative_path}' if relative_path != Path('.') else '/workspace'
            else:
                # No git root found, mount project directory as before
                volumes = {
                    str(project_path): {'bind': '/workspace', 'mode': 'rw'},
                }
                container_working_dir = '/workspace'
            
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
            
            # Mount host's npm global directory (includes Claude binary)
            try:
                result = subprocess.run(['npm', 'config', 'get', 'prefix'], 
                                      capture_output=True, text=True, check=True)
                npm_prefix = result.stdout.strip()
                if npm_prefix and Path(npm_prefix).exists():
                    # Handle spaces in path with temporary symlink
                    if ' ' in npm_prefix:
                        temp_link = Path('/tmp/npm-global-link')
                        temp_link.unlink(missing_ok=True)
                        temp_link.symlink_to(npm_prefix)
                        volumes[str(temp_link)] = {'bind': '/host-npm-global', 'mode': 'ro'}
                    else:
                        volumes[npm_prefix] = {'bind': '/host-npm-global', 'mode': 'ro'}
                else:
                    logger.warning("npm prefix directory not found")
            except subprocess.CalledProcessError:
                logger.warning("npm not found or failed to get prefix path")
            except Exception as e:
                logger.warning(f"Failed to setup npm global mount: {e}")
            
            # Get current user's UID and GID to run container with same permissions
            uid = os.getuid()
            gid = os.getgid()
            
            # Run container
            container = client.containers.run(
                image_name,
                command if isinstance(command, list) else ' '.join(command),
                volumes=volumes,
                working_dir=container_working_dir,
                detach=True,
                name=f"claude-task-{task.task_id[:8]}",
                # Don't set user - run as default container user (node) for proper permissions
                environment={
                    'CLAUDE_TASK_ID': task.task_id,
                    'CLAUDE_CONFIG_DIR': '/home/node/.claude',
                    'HOME': '/home/node',  # Ensure HOME is set for git
                    'CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS': 'true'  # Skip permissions check
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
            
            # Handle PR creation/update based on task type (only if GitHub is available)
            if task.branch_name and self.github_available:
                logger.info(f"Handling PR creation/update for task {task.task_id}")
                logger.info(f"Task metadata: {task.metadata}")
                logger.info(f"Working directory: {task.working_dir}")
                
                try:
                    github = GitHubIntegration(task.working_dir)
                    
                    # For feature tasks, create PR after completion
                    if task.metadata.get('type') == 'feature_task' and not task.pr_url:
                        logger.info(f"Creating PR for feature task on branch {task.branch_name}")
                        
                        # Check if PR already exists for this branch
                        existing_pr = github.get_pr_for_branch(task.branch_name)
                        logger.info(f"Existing PR check result: {existing_pr}")
                        
                        if not existing_pr:
                            # Create PR now that task is complete
                            task_description = task.metadata.get('task_description', 'Task completed')
                            pr_title = f"Task: {task_description}"
                            pr_body = f"""## Task Description
{task_description}

## Task Details
- Task ID: {task.task_id}
- Branch: {task.branch_name}
- Status: {"✅ Completed" if task.exit_code == 0 else "❌ Failed"}
- Exit Code: {task.exit_code}
- Started: {task.started_at.isoformat()}
- Completed: {task.completed_at.isoformat()}

---
This PR was automatically created by Claude Container after task completion."""
                            
                            logger.info(f"Creating PR with title: {pr_title}")
                            pr_url = github.create_pull_request(task.branch_name, pr_title, pr_body, draft=(task.exit_code != 0))
                            logger.info(f"PR creation result: {pr_url}")
                            
                            if pr_url:
                                task.pr_url = pr_url
                                task.output.append(f"\nPull request created: {pr_url}")
                                logger.info(f"Successfully created PR: {pr_url}")
                            else:
                                error_msg = "Failed to create pull request after task completion"
                                task.error.append(error_msg)
                                logger.error(f"{error_msg} for branch {task.branch_name}")
                        else:
                            task.pr_url = existing_pr
                            task.output.append(f"\nExisting pull request found: {existing_pr}")
                            logger.info(f"Found existing PR: {existing_pr}")
                    
                    # Update existing PR status
                    elif task.pr_url:
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
                
                except Exception as e:
                    error_msg = f"Exception during PR creation/update: {type(e).__name__}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    task.error.append(error_msg)
            
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
        logger.info("Shutting down daemon...")
        self.running = False
        if hasattr(self, 'socket'):
            try:
                self.socket.close()
                logger.info("Socket closed")
            except Exception as e:
                logger.error(f"Error closing socket: {e}")
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
                logger.info(f"Removed socket file {self.socket_path}")
            except Exception as e:
                logger.error(f"Error removing socket file: {e}")
        logger.info("Daemon shutdown complete")


def main():
    """Main entry point for the daemon."""
    try:
        logger.info("Task daemon process started")
        daemon = TaskDaemon()
        daemon.start()
    except Exception as e:
        logger.error(f"Fatal error in daemon main: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()