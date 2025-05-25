"""Client for communicating with the task daemon."""

import json
import socket
import logging
from typing import Dict, List, Optional

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DaemonClient:
    """Client for task daemon communication."""
    
    def __init__(self, socket_path: str = None):
        if socket_path is None:
            from pathlib import Path
            socket_path = str(Path.home() / ".claude-daemon.sock")
        self.socket_path = socket_path
    
    def _send_request(self, request: Dict) -> Dict:
        """Send a request to the daemon and get response."""
        logger.debug(f"Sending request to daemon: {request}")
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            logger.debug(f"Connecting to socket at {self.socket_path}")
            sock.connect(self.socket_path)
            
            request_data = json.dumps(request).encode('utf-8')
            logger.debug(f"Sending data: {len(request_data)} bytes")
            sock.send(request_data)
            
            logger.debug("Waiting for response...")
            response = sock.recv(8192).decode('utf-8')
            logger.debug(f"Received response: {response[:200]}..." if len(response) > 200 else f"Received response: {response}")
            
            parsed_response = json.loads(response)
            logger.debug(f"Parsed response: {parsed_response}")
            return parsed_response
        except FileNotFoundError:
            logger.error(f"Socket file not found at {self.socket_path}")
            return {"error": "Daemon not running (socket not found)"}
        except ConnectionRefusedError:
            logger.error("Connection refused by daemon")
            return {"error": "Daemon not accepting connections"}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response: {response}")
            return {"error": f"Invalid JSON response: {str(e)}"}
        except Exception as e:
            logger.error(f"Communication error: {type(e).__name__}: {str(e)}", exc_info=True)
            return {"error": f"Communication error: {str(e)}"}
        finally:
            sock.close()
            logger.debug("Socket closed")
    
    def submit_task(self, command: List[str], working_dir: str = None, env: Optional[Dict] = None, metadata: Optional[Dict] = None) -> Dict:
        """Submit a new task to the daemon."""
        logger.info(f"Submitting task: command={command[:2]}..., working_dir={working_dir}")
        logger.debug(f"Full command: {command}")
        logger.debug(f"Metadata: {metadata}")
        
        request = {
            "action": "submit",
            "command": command,
            "working_dir": working_dir or "."
        }
        if env:
            request["env"] = env
        if metadata:
            request["metadata"] = metadata
        
        return self._send_request(request)
    
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