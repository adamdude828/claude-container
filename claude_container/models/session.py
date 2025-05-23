"""Session model for Claude Code tasks."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class Session:
    """Represents a Claude Code session."""
    
    session_id: str
    name: str
    command: List[str]
    created_at: datetime
    status: str = "pending"  # pending, running, completed, failed, stopped
    container_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert session to dictionary."""
        return {
            'session_id': self.session_id,
            'name': self.name,
            'command': self.command,
            'created_at': self.created_at.isoformat(),
            'status': self.status,
            'container_id': self.container_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Session':
        """Create session from dictionary."""
        return cls(
            session_id=data['session_id'],
            name=data['name'],
            command=data['command'],
            created_at=datetime.fromisoformat(data['created_at']),
            status=data.get('status', 'pending'),
            container_id=data.get('container_id')
        )