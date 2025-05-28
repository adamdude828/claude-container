"""Client for communicating with the task daemon."""

import json
import socket
from typing import Dict, List


class DaemonClient:
    """Client for task daemon communication."""
    
    def __init__(self, socket_path: str = None):
        if socket_path is None:
            from pathlib import Path
            socket_path = str(Path.home() / ".claude-daemon.sock")
        self.socket_path = socket_path
    
    def _send_request(self, request: Dict) -> Dict:
        """Send a request to the daemon and get response."""
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(self.socket_path)
            sock.send(json.dumps(request).encode('utf-8'))
            
            response = sock.recv(8192).decode('utf-8')
            return json.loads(response)
        except FileNotFoundError:
            return {"error": "Daemon not running (socket not found)"}
        except ConnectionRefusedError:
            return {"error": "Daemon not accepting connections"}
        except Exception as e:
            return {"error": f"Communication error: {str(e)}"}
        finally:
            sock.close()
    
    def submit_task(self, command: List[str], working_dir: str = None) -> Dict:
        """Submit a new task to the daemon."""
        return self._send_request({
            "action": "submit",
            "command": command,
            "working_dir": working_dir or "."
        })
    
    def get_status(self, task_id: str) -> Dict:
        """Get task status."""
        return self._send_request({
            "action": "status",
            "task_id": task_id
        })
    
    def get_output(self, task_id: str) -> Dict:
        """Get task output."""
        return self._send_request({
            "action": "output",
            "task_id": task_id
        })
    
    def list_tasks(self) -> Dict:
        """List all tasks."""
        return self._send_request({
            "action": "list"
        })
    
    def kill_task(self, task_id: str) -> Dict:
        """Kill a running task."""
        return self._send_request({
            "action": "kill",
            "task_id": task_id
        })