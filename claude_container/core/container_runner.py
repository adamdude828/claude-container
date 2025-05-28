"""Container running functionality."""

from pathlib import Path
from typing import List, Optional, Dict
import subprocess
import docker.errors

from .docker_client import DockerClient
from ..utils.session_manager import SessionManager
from ..core.constants import DEFAULT_WORKDIR


class ContainerRunner:
    """Handles running containers with Claude Code."""
    
    def __init__(self, project_root: Path, data_dir: Path, image_name: str):
        """Initialize container runner."""
        self.project_root = project_root
        self.data_dir = data_dir
        self.image_name = image_name
        self.docker_client = DockerClient()
        self.session_manager = SessionManager(data_dir)
    
    def _get_container_environment(self, session_id: Optional[str] = None, 
                                   auto_approve: bool = False) -> Dict[str, str]:
        """Get standard environment variables for container."""
        env = {
            'CLAUDE_CONFIG_DIR': '/home/node/.claude',
            'NODE_OPTIONS': '--max-old-space-size=4096',
            'HOME': '/home/node'
        }
        
        if session_id:
            env['CLAUDE_SESSION_ID'] = session_id
            env['CLAUDE_CODE_AVAILABLE'] = '1'
            
        if auto_approve:
            env['CLAUDE_AUTO_APPROVE'] = 'true'
            
        return env
    
    def _get_container_config(self, command=None, tty=True, stdin_open=True, 
                              detach=False, remove=True, stdout=False, stderr=False,
                              session_id: Optional[str] = None, auto_approve: bool = False,
                              name: Optional[str] = None) -> Dict:
        """Get unified container configuration."""
        config = {
            'image': self.image_name,
            'volumes': self._get_volumes(),
            'working_dir': DEFAULT_WORKDIR,
            'environment': self._get_container_environment(session_id, auto_approve),
            'tty': tty,
            'stdin_open': stdin_open,
            'detach': detach,
            'remove': remove
        }
        
        if command:
            config['command'] = command
            
        if stdout:
            config['stdout'] = stdout
            
        if stderr:
            config['stderr'] = stderr
            
        if name:
            config['name'] = name
            
        return config
    
    def run_command(self, command: List[str]):
        """Run a command in the container."""
        # Check if Docker image exists
        if not self.docker_client.image_exists(self.image_name):
            print(f"Error: Docker image '{self.image_name}' not found.")
            print("Please run 'claude-container build' first to create the container image.")
            return
        
        # Handle command parsing
        if not command:
            cmd = ['/bin/bash']
            is_claude_cmd = False
            is_interactive_shell = True
        else:
            # Check if command needs shell interpretation
            if len(command) == 1 and (' ' in command[0] or "'" in command[0] or '"' in command[0]):
                # Use shell to handle quotes and spaces properly
                cmd = ['/bin/sh', '-c', command[0]]
                is_claude_cmd = 'claude' in command[0]
                is_interactive_shell = False
            else:
                # Use command as-is
                cmd = command
                is_claude_cmd = command[0] == 'claude'
                # Check if it's an interactive shell command
                is_interactive_shell = cmd[0] in ['/bin/bash', '/bin/sh', 'bash', 'sh']
        
        try:
            # Determine if this command needs interactive TTY
            needs_interactive = is_interactive_shell or (is_claude_cmd and (len(cmd) == 1 or (isinstance(cmd, list) and len(cmd) <= 2)))
            
            if needs_interactive:
                # For interactive commands, use subprocess for proper TTY handling
                self._run_interactive_container(cmd)
            elif is_claude_cmd:
                # For non-interactive claude commands, capture output to show on error
                config = self._get_container_config(
                    command=cmd,
                    tty=True,
                    stdin_open=False,
                    detach=True,
                    remove=False  # We'll remove it manually after getting logs
                )
                container = self.docker_client.client.containers.run(**config)
                
                # Wait for container to finish
                result = container.wait()
                exit_code = result.get('StatusCode', 0)
                
                if exit_code != 0:
                    # Get all logs for error diagnostics
                    logs = container.logs(stdout=True, stderr=True)
                    if isinstance(logs, bytes):
                        try:
                            error_output = logs.decode('utf-8')
                        except UnicodeDecodeError:
                            error_output = logs.decode('utf-8', errors='replace')
                    else:
                        error_output = logs
                    
                    # Clean up container
                    container.remove()
                    
                    # Show error with output
                    cmd_str = ' '.join(cmd) if isinstance(cmd, list) else str(cmd)
                    print(f"\nError: Command '{cmd_str}' failed with exit code {exit_code}")
                    print("\nContainer output:")
                    print(error_output.strip())
                    return
                else:
                    # Success - show output
                    logs = container.logs(stdout=True, stderr=True)
                    if isinstance(logs, bytes):
                        output = logs.decode('utf-8', errors='replace')
                    else:
                        output = logs
                    print(output.strip())
                    
                    # Clean up container
                    container.remove()
                
            else:
                # For other commands, capture both stdout and stderr
                config = self._get_container_config(
                    command=cmd,
                    tty=False,
                    stdin_open=False,
                    detach=False,
                    remove=True,
                    stdout=True,
                    stderr=True
                )
                result = self.docker_client.client.containers.run(**config)
                print(result.decode('utf-8') if isinstance(result, bytes) else result)
        except docker.errors.ContainerError as e:
            # More detailed error handling for container errors
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else str(cmd)
            print(f"Error: Command '{cmd_str}' in container returned non-zero exit status {e.exit_status}")
            
            # Show stderr if available
            if e.stderr:
                stderr_content = e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else e.stderr
                if stderr_content.strip():
                    print("\nError output (stderr):")
                    print(stderr_content)
            
            # Show stdout if available (sometimes errors go to stdout)
            if hasattr(e, 'output') and e.output:
                output_content = e.output.decode('utf-8') if isinstance(e.output, bytes) else e.output
                if output_content.strip():
                    print("\nStandard output:")
                    print(output_content)
        except Exception as e:
            print(f"Error running container: {e}")
    
    def start_task(self, task_description: Optional[str] = None, 
                   continue_session: Optional[str] = None):
        """Start a new Claude Code task or continue an existing session."""
        
        # Handle session
        if continue_session:
            session = self.session_manager.get_session(continue_session)
            if not session:
                raise ValueError(f"Session {continue_session} not found")
            task_description = session.name
            session_id = session.session_id
        else:
            # Create session with task description as name and claude command
            claude_command = ['claude']
            if task_description:
                claude_command.append(task_description)
            session = self.session_manager.create_session(
                name=task_description or "Interactive Claude session",
                command=claude_command
            )
            session_id = session.session_id
        
        # Prepare Claude command
        claude_cmd = ['claude']
        if continue_session:
            claude_cmd.extend(['--resume', session_id])
        if task_description:
            claude_cmd.append(task_description)
        
        # For interactive Claude tasks, use subprocess
        self._run_interactive_container(claude_cmd, session_id=session_id)
        
        # Mark session as completed
        self.session_manager.mark_completed(session_id)
    
    def _get_volumes(self) -> Dict[str, Dict[str, str]]:
        """Get volume mappings for the container."""
        volumes = {
            # Mount project directory to workspace
            str(self.project_root): {'bind': DEFAULT_WORKDIR, 'mode': 'rw'}
        }
        
        # Mount Claude directory if it exists
        claude_dir = Path.home() / '.claude'
        if claude_dir.exists():
            volumes[str(claude_dir)] = {'bind': '/home/node/.claude', 'mode': 'rw'}
        
        # Mount .claude.json file if it exists (this is where auth is stored)
        claude_json = Path.home() / '.claude.json'
        if claude_json.exists():
            volumes[str(claude_json)] = {'bind': '/home/node/.claude.json', 'mode': 'rw'}
        
        # Mount .config/claude directory if it exists (this is where auth is stored)
        config_claude_dir = Path.home() / '.config' / 'claude'
        if config_claude_dir.exists():
            volumes[str(config_claude_dir)] = {'bind': '/home/node/.config/claude', 'mode': 'rw'}
        
        # Mount SSH directory if it exists (for git operations)
        ssh_dir = Path.home() / '.ssh'
        if ssh_dir.exists():
            volumes[str(ssh_dir)] = {'bind': '/home/node/.ssh', 'mode': 'ro'}
        
        # Mount GitHub CLI config if it exists
        gh_config_dir = Path.home() / '.config' / 'gh'
        if gh_config_dir.exists():
            volumes[str(gh_config_dir)] = {'bind': '/home/node/.config/gh', 'mode': 'ro'}
        
        # Mount git config if it exists
        gitconfig = Path.home() / '.gitconfig'
        if gitconfig.exists():
            volumes[str(gitconfig)] = {'bind': '/home/node/.gitconfig', 'mode': 'ro'}
        
        # No need to mount npm global directory since Claude Code is installed in the container
        
        return volumes
    
    def run_async(self, command: List[str], session_id: str):
        """Run a command asynchronously in the background."""
        
        # Handle empty command - don't default to bash for async runs
        if not command:
            print("Error: No command provided for async run")
            return None
            
        cmd = ' '.join(command)
        
        # Check if Docker image exists
        if not self.docker_client.image_exists(self.image_name):
            print(f"Error: Docker image '{self.image_name}' not found.")
            print("Please run 'claude-container build' first to create the container image.")
            return None
        
        # Determine if this is a long-running command (claude) vs short command
        is_claude_command = command and command[0] == 'claude'
        
        try:
            # Run container in detached mode with unified config
            config = self._get_container_config(
                command=cmd,
                tty=is_claude_command,  # Only use tty for interactive claude commands
                stdin_open=is_claude_command,  # Only keep stdin open for claude commands
                detach=True,
                remove=False,  # Don't auto-remove async containers
                session_id=session_id,
                auto_approve=True,  # Auto-approve permissions for async mode
                name=f"claude-async-{session_id[:8]}"  # Use shorter ID for container name
            )
            container = self.docker_client.client.containers.run(**config)
            return container
        except Exception as e:
            print(f"Error starting async container: {e}")
            return None
    
    def _run_interactive_container(self, cmd, session_id: Optional[str] = None):
        """Run an interactive container using subprocess for proper TTY handling."""
        # Build docker run command
        docker_cmd = [
            'docker', 'run', 
            '--rm',  # Remove container after exit
            '-it',   # Interactive with TTY
            '-w', DEFAULT_WORKDIR,
        ]
        
        # Add environment variables
        env = self._get_container_environment(session_id=session_id)
        for key, value in env.items():
            docker_cmd.extend(['-e', f'{key}={value}'])
        
        # Add volume mounts
        volumes = self._get_volumes()
        for host_path, mount_info in volumes.items():
            bind_path = mount_info['bind']
            mode = mount_info.get('mode', 'rw')
            docker_cmd.extend(['-v', f'{host_path}:{bind_path}:{mode}'])
        
        # Add image and command
        docker_cmd.append(self.image_name)
        docker_cmd.extend(cmd)
        
        # Run with subprocess for proper TTY handling
        subprocess.run(docker_cmd)
    
    def _attach_and_cleanup(self, container):
        """Attach to container and clean up when done."""
        try:
            for line in container.attach(stream=True, logs=True):
                print(line.decode('utf-8'), end='')
        except KeyboardInterrupt:
            pass
        finally:
            container.stop()
            container.remove()