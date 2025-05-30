import docker
import json
import os
import shutil
import subprocess
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime


class DockerManager:
    def __init__(self, project_root: Path, data_dir: Path):
        self.project_root = project_root
        self.data_dir = data_dir
        try:
            self.client = docker.from_env()
            # Test connection to Docker daemon
            self.client.ping()
        except docker.errors.DockerException as e:
            if "connection refused" in str(e).lower() or "cannot connect" in str(e).lower():
                raise RuntimeError(
                    "Docker daemon is not running. Please start Docker Desktop or the Docker service."
                ) from e
            else:
                raise RuntimeError(f"Failed to connect to Docker: {e}") from e
        self.config_file = data_dir / 'container_config.json'
        self.image_name = f"claude-container-{project_root.name}".lower()
    
    
    
    def run_container(self, command: List[str]):
        """Run container with Claude Code installed"""
        volumes = {
            str(self.project_root): {'bind': '/workspace', 'mode': 'rw'},
            str(Path.home() / '.ssh'): {'bind': '/root/.ssh', 'mode': 'ro'},
        }
        
        # Mount Claude configuration if it exists
        claude_config = Path.home() / '.claude.json'
        if claude_config.exists():
            volumes[str(claude_config)] = {'bind': '/root/.claude.json', 'mode': 'ro'}
        
        # Mount GitHub CLI config if it exists
        gh_config_dir = Path.home() / '.config' / 'gh'
        if gh_config_dir.exists():
            volumes[str(gh_config_dir)] = {'bind': '/root/.config/gh', 'mode': 'ro'}
        
        # Prepare command
        if command:
            cmd = ' '.join(command)
        else:
            cmd = '/bin/bash'
        
        container = self.client.containers.run(
            self.image_name,
            cmd,
            volumes=volumes,
            working_dir='/workspace',
            tty=True,
            stdin_open=True,
            detach=True
        )
        
        # Attach to container
        try:
            for line in container.attach(stream=True, logs=True):
                print(line.decode('utf-8'), end='')
        except KeyboardInterrupt:
            pass
        finally:
            container.stop()
            container.remove()
    
    def _generate_default_dockerfile(self, existing_dockerfile: str = None) -> str:
        """Generate a default Dockerfile for Claude Code"""
        # Detect project type
        is_python = (self.project_root / 'requirements.txt').exists() or (self.project_root / 'pyproject.toml').exists()
        is_node = (self.project_root / 'package.json').exists()
        
        if is_python:
            base_image = "python:3.11"
        elif is_node:
            base_image = "node:20"
        else:
            base_image = "ubuntu:22.04"
        
        dockerfile = f"""FROM {base_image}

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    git \\
    curl \\
    wget \\
    build-essential \\
    ca-certificates \\
    gnupg \\
    lsb-release \\
    && rm -rf /var/lib/apt/lists/*

# Install Node.js if not already in base image
"""
        if not is_node:
            dockerfile += """RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && \\
    apt-get install -y nodejs

"""
        
        dockerfile += """# Install Claude Code globally
RUN npm install -g @anthropic-ai/claude-code

# Install GitHub CLI
RUN (type -p wget >/dev/null || (apt update && apt-get install wget -y)) && \\
    mkdir -p -m 755 /etc/apt/keyrings && \\
    wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null && \\
    chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg && \\
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \\
    apt update && \\
    apt install gh -y && \\
    gh --version

# Set working directory
WORKDIR /workspace

# Default command
CMD ["claude"]
"""
        return dockerfile
    
    def find_claude_code(self) -> Optional[str]:
        """Try to find Claude Code executable"""
        # Common locations
        paths = [
            '/usr/local/bin/claude',
            '/opt/homebrew/bin/claude',
            '/usr/bin/claude',
            '/Applications/Claude Code.app/Contents/MacOS/Claude Code',
        ]
        
        for path in paths:
            if os.path.exists(path):
                return path
        
        # Try which command
        try:
            result = subprocess.run(['which', 'claude'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        # Check in PATH
        for path_dir in os.environ.get('PATH', '').split(':'):
            path = Path(path_dir) / 'claude'
            if path.exists():
                return path
        
        return None
    
    def build_with_claude(self, claude_code_path: str, force_rebuild: bool = False, existing_dockerfile: str = None) -> str:
        """Use Claude Code to generate and build Dockerfile"""
        if not force_rebuild and self._image_exists():
            return self.image_name
        
        # If force rebuild, remove existing image
        if force_rebuild and self._image_exists():
            try:
                print(f"Removing existing image: {self.image_name}")
                self.client.images.remove(self.image_name, force=True)
            except Exception as e:
                print(f"Warning: Could not remove existing image: {e}")
        
        # Manage Claude Code permissions
        claude_config_path = Path.home() / '.claude.json'
        backup_config_path = Path.home() / '.claude.json.backup'
        original_config = None
        
        try:
            # Backup existing config if it exists
            if claude_config_path.exists():
                original_config = claude_config_path.read_text()
                shutil.copy2(claude_config_path, backup_config_path)
            
            # Create temporary config with Docker permissions
            temp_config = {
                "toolPermissions": {
                    "allow": [
                        "Bash(docker build*)",
                        "Bash(docker run*)",
                        "Bash(docker images*)",
                        "Bash(docker ps*)",
                        "Bash(apt-get*)",
                        "Bash(npm*)",
                        "Bash(node*)",
                        "Read(*)",
                        "Write(*)"
                    ]
                }
            }
            
            # If original config exists, merge permissions
            if original_config:
                try:
                    original_json = json.loads(original_config)
                    if "toolPermissions" in original_json:
                        if "allow" in original_json["toolPermissions"]:
                            # Merge allow lists
                            existing_allows = original_json["toolPermissions"]["allow"]
                            temp_config["toolPermissions"]["allow"].extend(existing_allows)
                            # Remove duplicates while preserving order
                            temp_config["toolPermissions"]["allow"] = list(dict.fromkeys(temp_config["toolPermissions"]["allow"]))
                        if "deny" in original_json["toolPermissions"]:
                            temp_config["toolPermissions"]["deny"] = original_json["toolPermissions"]["deny"]
                except:
                    pass  # If parsing fails, use our default config
            
            # Write temporary config
            claude_config_path.write_text(json.dumps(temp_config, indent=2))
            print("Temporarily enabled Docker permissions for Claude Code")
            
            # Create temporary Dockerfile path
            temp_dockerfile = self.data_dir / 'Dockerfile.claude'
            
            # Prepare prompt for Claude
            prompt = f"""Generate a Dockerfile for running Claude Code in this project.

IMPORTANT: 
- This container will run Claude Code (installed via npm)
- The project directory will be mounted at /workspace
- DO NOT install project dependencies (npm install, pip install, etc) - they will be copied from host
- DO NOT copy source files - the project will be mounted

MANDATORY REQUIREMENTS:
1. Choose appropriate base image for the project type (avoid slim images if they cause apt-get errors)
2. Install system-level tools: git, build-essential, curl, wget, ca-certificates, gnupg, lsb-release
3. MUST install Node.js (latest LTS) - required for Claude Code
4. MUST install Claude Code globally: RUN npm install -g @anthropic-ai/claude-code
5. MUST install GitHub CLI (gh) - required for GitHub operations
6. Set WORKDIR to /workspace
7. Install language runtimes/compilers if needed (python, rust, etc)
8. DO NOT run package managers to install project dependencies
{f'9. Reference the {existing_dockerfile} but remember dependencies come from host' if existing_dockerfile else ''}

TESTING REQUIREMENTS:
- You have permission to run Docker commands (docker build, docker run, etc.)
- Please TEST the Dockerfile by building it with: docker build -f <dockerfile> .
- If the build fails, analyze the error and regenerate a fixed version
- Ensure all RUN commands complete successfully (exit code 0)
- If apt-get update fails with error 100, try using a full base image (not slim)

Docker permissions are configured in Claude Code settings to allow:
- Bash(docker build*)
- Bash(docker run*)
- Bash(docker images*)

Output ONLY the final working Dockerfile content after testing, no explanations or markdown."""

            # Run Claude Code to generate Dockerfile
            # Give Claude Code enough time to test the Docker build
            result = subprocess.run(
                [claude_code_path, '-p', prompt],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout for testing builds
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Claude Code failed to generate Dockerfile: {result.stderr}")
            
            # Extract Dockerfile content from output
            dockerfile_content = result.stdout.strip()
            
            # Clean up markdown formatting if present
            if '```dockerfile' in dockerfile_content or '```Dockerfile' in dockerfile_content:
                # Extract content between ```dockerfile and ```
                match = re.search(r'```[Dd]ockerfile\s*\n(.*?)```', dockerfile_content, re.DOTALL)
                if match:
                    dockerfile_content = match.group(1).strip()
            
            # Write the Dockerfile
            temp_dockerfile.write_text(dockerfile_content)
            
            # Build image using generated Dockerfile
            try:
                self.client.images.build(
                    path=str(self.project_root),
                    dockerfile=str(temp_dockerfile),
                    tag=self.image_name,
                    rm=True
                )
                
                # Save config
                self._save_config({
                    'type': 'claude-generated',
                    'generated_at': datetime.now().isoformat()
                })
            except Exception:
                # Log error but keep Dockerfile for debugging
                print(f"Build failed. Dockerfile saved at: {temp_dockerfile}")
                raise
            else:
                # Only clean up on success
                if temp_dockerfile.exists():
                    temp_dockerfile.unlink()
            
            return self.image_name
            
        finally:
            # Always restore original config
            if original_config is not None:
                claude_config_path.write_text(original_config)
                print("Restored original Claude Code configuration")
            elif claude_config_path.exists() and backup_config_path.exists():
                # If we created a new config but had no original, remove it
                claude_config_path.unlink()
                print("Removed temporary Claude Code configuration")
            
            # Clean up backup file if it exists
            if backup_config_path.exists():
                backup_config_path.unlink()
    
    def cleanup(self):
        """Clean up container resources"""
        try:
            # Remove image
            self.client.images.remove(self.image_name, force=True)
        except:
            pass
        
        # Remove data directory
        if self.data_dir.exists():
            shutil.rmtree(self.data_dir)
    
    def _image_exists(self) -> bool:
        """Check if image already exists"""
        try:
            self.client.images.get(self.image_name)
            return True
        except docker.errors.ImageNotFound:
            return False
    
    def _save_config(self, config: Dict[str, Any]):
        """Save container configuration"""
        self.config_file.write_text(json.dumps(config, indent=2))
    
    def _load_config(self) -> Optional[Dict[str, Any]]:
        """Load container configuration"""
        if not self.config_file.exists():
            return None
        return json.loads(self.config_file.read_text())
    
    
    def check_git_ssh_origin(self) -> bool:
        """Check if Git remote origin uses SSH"""
        try:
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                origin_url = result.stdout.strip()
                return origin_url.startswith('git@') or 'ssh://' in origin_url
            return True  # No git repo, allow to proceed
        except:
            return True  # If git check fails, allow to proceed
    
