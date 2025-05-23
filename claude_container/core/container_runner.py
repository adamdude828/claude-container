"""Container running functionality."""

from pathlib import Path
from typing import List, Optional, Dict

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
    
    def run_command(self, command: List[str]):
        """Run a command in the container."""
        volumes = self._get_volumes()
        cmd = ' '.join(command) if command else '/bin/bash'
        
        try:
            # Check if this is a claude command
            if command and command[0] == 'claude':
                # For claude commands, don't capture output - let it stream
                self.docker_client.client.containers.run(
                    self.image_name,
                    cmd,
                    volumes=volumes,
                    working_dir=DEFAULT_WORKDIR,
                    tty=True,
                    stdin_open=False,  # No stdin for -p commands
                    remove=True
                )
            else:
                # For other commands, capture and print output
                result = self.docker_client.client.containers.run(
                    self.image_name,
                    cmd,
                    volumes=volumes,
                    working_dir=DEFAULT_WORKDIR,
                    tty=False,
                    remove=True,
                    stdout=True,
                    stderr=True
                )
                print(result.decode('utf-8') if isinstance(result, bytes) else result)
        except Exception as e:
            print(f"Error running container: {e}")
    
    def start_task(self, task_description: Optional[str] = None, 
                   continue_session: Optional[str] = None):
        """Start a new Claude Code task or continue an existing session."""
        volumes = self._get_volumes()
        
        # Handle session
        if continue_session:
            session = self.session_manager.get_session(continue_session)
            if not session:
                raise ValueError(f"Session {continue_session} not found")
            task_description = session.task
            session_id = continue_session
        else:
            session = self.session_manager.create_session(task_description)
            session_id = session.id
        
        # Prepare Claude command
        claude_cmd = ['claude']
        if continue_session:
            claude_cmd.extend(['--resume', session_id])
        if task_description:
            claude_cmd.append(task_description)
        
        # Run container
        container = self.docker_client.run_container(
            self.image_name,
            ' '.join(claude_cmd),
            volumes=volumes,
            working_dir=DEFAULT_WORKDIR,
            tty=True,
            stdin_open=True,
            detach=True,
            environment={
                'CLAUDE_CODE_AVAILABLE': '1',
                'CLAUDE_SESSION_ID': session_id
            }
        )
        
        try:
            self._attach_and_cleanup(container)
        finally:
            # Mark session as completed
            self.session_manager.mark_completed(session_id)
    
    def _get_volumes(self) -> Dict[str, Dict[str, str]]:
        """Get volume mappings for the container."""
        volumes = {
            str(self.project_root): {'bind': DEFAULT_WORKDIR, 'mode': 'rw'},
        }
        
        # Always mount Claude configuration (read-write so Claude can update trusted folders)
        claude_config = Path.home() / '.claude.json'
        if claude_config.exists():
            volumes[str(claude_config)] = {'bind': '/root/.claude.json', 'mode': 'rw'}
        else:
            print("Warning: ~/.claude.json not found. Claude Code may not have access to your settings.")
        
        # Mount Claude directory if it exists
        claude_dir = Path.home() / '.claude'
        if claude_dir.exists():
            volumes[str(claude_dir)] = {'bind': '/root/.claude', 'mode': 'rw'}
        
        # Mount SSH directory if it exists
        ssh_dir = Path.home() / '.ssh'
        if ssh_dir.exists():
            volumes[str(ssh_dir)] = {'bind': '/root/.ssh', 'mode': 'ro'}
        
        # Mount GitHub CLI config if it exists
        gh_config_dir = Path.home() / '.config' / 'gh'
        if gh_config_dir.exists():
            volumes[str(gh_config_dir)] = {'bind': '/root/.config/gh', 'mode': 'ro'}
        
        return volumes
    
    def run_async(self, command: List[str], session_id: str):
        """Run a command asynchronously in the background."""
        volumes = self._get_volumes()
        cmd = ' '.join(command) if command else '/bin/bash'
        
        # Check if image exists locally
        try:
            self.docker_client.client.images.get(self.image_name)
        except:
            print(f"Error: Image '{self.image_name}' not found. Please run 'build' first.")
            return None
        
        try:
            # Run container in detached mode
            container = self.docker_client.client.containers.run(
                self.image_name,
                cmd,
                volumes=volumes,
                working_dir=DEFAULT_WORKDIR,
                tty=True,
                stdin_open=True,
                detach=True,
                name=f"claude-async-{session_id[:8]}",  # Use shorter ID for container name
                environment={
                    'CLAUDE_SESSION_ID': session_id,
                    'CLAUDE_AUTO_APPROVE': 'true'  # Auto-approve permissions for async mode
                }
            )
            return container
        except Exception as e:
            print(f"Error starting async container: {e}")
            return None
    
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