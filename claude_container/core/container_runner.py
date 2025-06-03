"""Container running functionality."""

from pathlib import Path
from typing import List, Optional, Dict
import subprocess
import uuid

from ..services.docker_service import DockerService
from ..services.exceptions import DockerServiceError
from ..core.constants import DEFAULT_WORKDIR, CONTAINER_PREFIX


class ContainerRunner:
    """Handles running containers with Claude Code."""
    
    def __init__(self, project_root: Path, data_dir: Path, image_name: str):
        """Initialize container runner."""
        self.project_root = project_root
        self.data_dir = data_dir
        self.image_name = image_name
        self.docker_service = DockerService()
    
    def _get_container_environment(self, auto_approve: bool = False) -> Dict[str, str]:
        """Get standard environment variables for container."""
        env = {
            'CLAUDE_CONFIG_DIR': '/root/.claude',
            'NODE_OPTIONS': '--max-old-space-size=4096',
            'HOME': '/root'
        }
            
        if auto_approve:
            env['CLAUDE_AUTO_APPROVE'] = 'true'
            
        return env
    
    def _get_container_config(self, command=None, tty=True, stdin_open=True, 
                              detach=False, remove=True, stdout=False, stderr=False,
                              auto_approve: bool = False,
                              name: Optional[str] = None,
                              user: Optional[str] = None) -> Dict:
        """Get unified container configuration."""
        config = {
            'image': self.image_name,
            'volumes': self._get_volumes(),
            'working_dir': DEFAULT_WORKDIR,
            'environment': self._get_container_environment(auto_approve),
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
            
        if user:
            config['user'] = user
            
        return config
    
    def run_command(self, command: List[str], user: Optional[str] = None):
        """Run a command in the container."""
        # Check if Docker image exists
        if not self.docker_service.image_exists(self.image_name):
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
                self._run_interactive_container(cmd, user=user)
            elif is_claude_cmd:
                # For non-interactive claude commands, capture output to show on error
                config = self._get_container_config(
                    command=cmd,
                    tty=True,
                    stdin_open=False,
                    detach=True,
                    remove=False,  # We'll remove it manually after getting logs
                    user=user
                )
                container = self.docker_service.run_container(
                    **config
                )
                
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
                    stderr=True,
                    user=user
                )
                result = self.docker_service.run_container(
                    **config
                )
                print(result.decode('utf-8') if isinstance(result, bytes) else result)
        except DockerServiceError as e:
            # More detailed error handling for container errors
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else str(cmd)
            print(f"Error running command '{cmd_str}': {e}")
        except Exception as e:
            print(f"Error running container: {e}")
    
    
    def _get_volumes(self) -> Dict[str, Dict[str, str]]:
        """Get volume mappings for the container."""
        volumes = {}
        
        # Mount Claude directory if it exists
        claude_dir = Path.home() / '.claude'
        if claude_dir.exists():
            volumes[str(claude_dir)] = {'bind': '/root/.claude', 'mode': 'rw'}
        
        # Mount .claude.json file if it exists (this is where auth is stored)
        claude_json = Path.home() / '.claude.json'
        if claude_json.exists():
            volumes[str(claude_json)] = {'bind': '/root/.claude.json', 'mode': 'rw'}
        
        # Mount .config/claude directory if it exists (this is where auth is stored)
        config_claude_dir = Path.home() / '.config' / 'claude'
        if config_claude_dir.exists():
            volumes[str(config_claude_dir)] = {'bind': '/root/.config/claude', 'mode': 'rw'}
        
        # Mount SSH directory if it exists (for git operations)
        ssh_dir = Path.home() / '.ssh'
        if ssh_dir.exists():
            volumes[str(ssh_dir)] = {'bind': '/root/.ssh', 'mode': 'ro'}
        
        # Mount GitHub CLI config if it exists
        gh_config_dir = Path.home() / '.config' / 'gh'
        if gh_config_dir.exists():
            volumes[str(gh_config_dir)] = {'bind': '/root/.config/gh', 'mode': 'ro'}
        
        # No need to mount npm global directory since Claude Code is installed in the container
        
        # Do not mount project directory - as per project requirements
        
        return volumes
    
    
    def _run_interactive_container(self, cmd, user: Optional[str] = None):
        """Run an interactive container using subprocess for proper TTY handling."""
        # Build docker run command
        docker_cmd = [
            'docker', 'run', 
            '--rm',  # Remove container after exit
            '-it',   # Interactive with TTY
            '-w', DEFAULT_WORKDIR,
        ]
        
        # Add environment variables
        env = self._get_container_environment()
        for key, value in env.items():
            docker_cmd.extend(['-e', f'{key}={value}'])
        
        # Add volume mounts
        volumes = self._get_volumes()
        for host_path, mount_info in volumes.items():
            bind_path = mount_info['bind']
            mode = mount_info.get('mode', 'rw')
            docker_cmd.extend(['-v', f'{host_path}:{bind_path}:{mode}'])
        
        # Add user if specified
        if user:
            docker_cmd.extend(['--user', user])
        
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
    
    def create_persistent_container(self, name_suffix: str = "task"):
        """Create a persistent container for multi-step operations.
        
        Container naming strategy:
        - Prefix: {CONTAINER_PREFIX}-{name_suffix}-{project_name}
        - Suffix: Random 8-character UUID hex
        
        This allows easy identification and cleanup of task containers.
        """
        # Generate a unique container name with deterministic prefix and random suffix
        random_suffix = uuid.uuid4().hex[:8]
        container_name = f"{CONTAINER_PREFIX}-{name_suffix}-{self.project_root.name}-{random_suffix}".lower()
        
        config = self._get_container_config(
            command="sleep infinity",  # Keep container running
            tty=False,
            stdin_open=False,
            detach=True,
            remove=False,  # Don't auto-remove
            name=container_name
        )
        
        # Add labels for easy identification and filtering
        config['labels'] = {
            "claude-container": "true",
            "claude-container-type": name_suffix,
            "claude-container-project": self.project_root.name.lower(),
            "claude-container-prefix": CONTAINER_PREFIX
        }
        
        try:
            container = self.docker_service.run_container(**config)
            return container
        except Exception as e:
            raise RuntimeError(f"Failed to create container: {e}")
    
    def write_file(self, container, file_path: str, content: str) -> None:
        """Write a file inside a running container.
        
        Args:
            container: Docker container object
            file_path: Path inside container to write to
            content: Content to write to the file
        """
        # Escape content for shell
        escaped_content = content.replace("'", "'\"'\"'")
        
        # Use echo with heredoc for reliable content writing
        command = f"sh -c 'cat > {file_path} << '\''EOF'\''\n{escaped_content}\nEOF'"
        
        try:
            result = self.docker_service.exec_in_container(
                container,
                command,
                stream=False,
                tty=False
            )
            
            # Check if command succeeded
            # exec_in_container returns a dict for non-streaming calls
            if isinstance(result, dict):
                exit_code = result.get('ExitCode', 1)
                if exit_code != 0:
                    stderr = result.get('stderr', b'').decode('utf-8')
                    raise RuntimeError(f"Failed to write file: {stderr}")
            else:
                # Handle ExecResult object (shouldn't happen with stream=False)
                exit_code = result.exit_code if hasattr(result, 'exit_code') else result[0]
                if exit_code != 0:
                    output = result.output if hasattr(result, 'output') else result[1]
                    if isinstance(output, bytes):
                        output = output.decode('utf-8')
                    raise RuntimeError(f"Failed to write file: {output}")
                
        except Exception as e:
            raise RuntimeError(f"Failed to write file {file_path}: {e}")
    
    def exec_in_container_as_user(self, container, command, user: str = "node", **kwargs):
        """Execute command in container as specified user.
        
        Args:
            container: Docker container object
            command: Command to execute (string or list)
            user: User to run command as (default: "node")
            **kwargs: Additional arguments passed to exec_run
            
        Returns:
            Result from container.exec_run
        """
        # First, ensure the workspace is owned by the target user
        if user == "node":
            chown_result = container.exec_run(['chown', '-R', 'node:node', '/workspace'])
            if chown_result.exit_code != 0:
                print(f"Warning: Failed to change ownership of /workspace: {chown_result.output.decode('utf-8')}")
        
        # If command is a string, keep it as a string for proper shell execution
        if isinstance(command, str):
            # Use su to switch to the specified user with the command as a single string
            command_with_user = ['su', '-', user, '-c', command]
        else:
            # If command is a list, join it properly for shell execution
            shell_command = ' '.join(command)
            command_with_user = ['su', '-', user, '-c', shell_command]
        
        return container.exec_run(command_with_user, **kwargs)