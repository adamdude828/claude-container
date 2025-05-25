"""GitHub integration for Claude Container."""

import subprocess
import json
import os
import logging
from typing import Optional, Dict, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class GitHubIntegration:
    """Handle GitHub operations for Claude tasks."""
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir).resolve()
        
    def create_branch(self, branch_name: str) -> bool:
        """Create and push a new branch."""
        try:
            # Save current directory
            original_dir = os.getcwd()
            os.chdir(self.project_dir)
            
            # Create and checkout branch
            subprocess.run(['git', 'checkout', '-b', branch_name], 
                         check=True, capture_output=True, text=True)
            
            # Push branch to origin
            subprocess.run(['git', 'push', '-u', 'origin', branch_name],
                         check=True, capture_output=True, text=True)
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating branch: {e.stderr}")
            return False
        finally:
            os.chdir(original_dir)
    
    
    def update_pr_description(self, pr_number: str, description: str) -> bool:
        """Update PR description."""
        try:
            original_dir = os.getcwd()
            os.chdir(self.project_dir)
            
            subprocess.run([
                'gh', 'pr', 'edit', pr_number,
                '--body', description
            ], check=True, capture_output=True, text=True)
            
            return True
        except subprocess.CalledProcessError:
            return False
        finally:
            os.chdir(original_dir)
    
    def mark_pr_ready(self, pr_number: str) -> bool:
        """Mark PR as ready for review."""
        try:
            original_dir = os.getcwd()
            os.chdir(self.project_dir)
            
            subprocess.run([
                'gh', 'pr', 'ready', pr_number
            ], check=True, capture_output=True, text=True)
            
            return True
        except subprocess.CalledProcessError:
            return False
        finally:
            os.chdir(original_dir)
    
    def get_pr_number_from_url(self, pr_url: str) -> Optional[str]:
        """Extract PR number from URL."""
        # URL format: https://github.com/owner/repo/pull/123
        parts = pr_url.strip().split('/')
        if len(parts) >= 2 and parts[-2] == 'pull':
            return parts[-1]
        return None
    
    def check_git_status(self) -> Tuple[bool, str]:
        """Check if git working directory is clean."""
        try:
            original_dir = os.getcwd()
            os.chdir(self.project_dir)
            
            result = subprocess.run(['git', 'status', '--porcelain'],
                                  capture_output=True, text=True, check=True)
            
            is_clean = len(result.stdout.strip()) == 0
            return is_clean, result.stdout
            
        except subprocess.CalledProcessError as e:
            return False, str(e)
        finally:
            os.chdir(original_dir)
    
    def get_current_branch(self) -> Optional[str]:
        """Get current git branch name."""
        try:
            original_dir = os.getcwd()
            os.chdir(self.project_dir)
            
            result = subprocess.run(['git', 'branch', '--show-current'],
                                  capture_output=True, text=True, check=True)
            
            return result.stdout.strip()
            
        except subprocess.CalledProcessError:
            return None
        finally:
            os.chdir(original_dir)
    
    def get_pr_for_branch(self, branch_name: str) -> Optional[str]:
        """Check if a PR already exists for the given branch."""
        try:
            original_dir = os.getcwd()
            os.chdir(self.project_dir)
            
            logger.info(f"Checking for existing PR on branch: {branch_name}")
            
            # List PRs for the branch
            cmd = [
                'gh', 'pr', 'list',
                '--head', branch_name,
                '--json', 'url',
                '--limit', '1'
            ]
            
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            logger.info(f"PR list stdout: {result.stdout}")
            logger.info(f"PR list stderr: {result.stderr}")
            
            prs = json.loads(result.stdout)
            if prs:
                pr_url = prs[0]['url']
                logger.info(f"Found existing PR: {pr_url}")
                return pr_url
            
            logger.info("No existing PR found")
            return None
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error checking for PR: {e}")
            logger.error(f"Stdout: {e.stdout}")
            logger.error(f"Stderr: {e.stderr}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing PR list JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error checking for PR: {type(e).__name__}: {str(e)}", exc_info=True)
            return None
        finally:
            os.chdir(original_dir)
    
    def create_pull_request(self, branch_name: str, title: str, body: str, draft: bool = True) -> Optional[str]:
        """Create a pull request and return its URL."""
        try:
            # Save current directory
            original_dir = os.getcwd()
            os.chdir(self.project_dir)
            
            logger.info(f"Creating PR in directory: {self.project_dir}")
            logger.info(f"Branch: {branch_name}, Draft: {draft}")
            
            # Build command
            cmd = [
                'gh', 'pr', 'create',
                '--title', title,
                '--body', body,
                '--head', branch_name
            ]
            if draft:
                cmd.append('--draft')
            
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # Create PR
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Extract PR URL from output
            pr_url = result.stdout.strip()
            logger.info(f"PR creation stdout: {result.stdout}")
            logger.info(f"PR creation stderr: {result.stderr}")
            
            return pr_url if pr_url else None
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating PR: {e}")
            logger.error(f"Command: {' '.join(e.cmd)}")
            logger.error(f"Return code: {e.returncode}")
            logger.error(f"Stdout: {e.stdout}")
            logger.error(f"Stderr: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating PR: {type(e).__name__}: {str(e)}", exc_info=True)
            return None
        finally:
            os.chdir(original_dir)