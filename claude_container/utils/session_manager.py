"""Session management utilities."""

import json
import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..models.session import Session
from ..core.constants import SESSIONS_FILE_NAME


class SessionManager:
    """Manages Claude Code sessions."""
    
    def __init__(self, data_dir: Path):
        """Initialize session manager."""
        self.data_dir = data_dir
        self.sessions_file = data_dir / SESSIONS_FILE_NAME
    
    def create_session(self, name: str, command: List[str]) -> Session:
        """Create a new session."""
        session = Session(
            session_id=str(uuid.uuid4()),
            name=name,
            command=command,
            created_at=datetime.now(),
            status="pending"
        )
        self._save_session(session)
        return session
    
    def get_session(self, session_id_or_name: str) -> Optional[Session]:
        """Get a specific session by ID or name."""
        sessions = self.list_sessions()
        for session in sessions:
            if session.session_id == session_id_or_name or session.name == session_id_or_name:
                return session
        return None
    
    def save_session(self, session: Session):
        """Update an existing session."""
        sessions = self.list_sessions()
        for i, s in enumerate(sessions):
            if s.session_id == session.session_id:
                sessions[i] = session
                self._save_all_sessions(sessions)
                return
        # If not found, add it
        self._save_session(session)
    
    def list_sessions(self) -> List[Session]:
        """List all sessions."""
        if not self.sessions_file.exists():
            return []
        
        try:
            data = json.loads(self.sessions_file.read_text())
            return [Session.from_dict(item) for item in data]
        except:
            return []
    
    def mark_completed(self, session_id: str):
        """Mark a session as completed."""
        session = self.get_session(session_id)
        if session:
            session.status = "completed"
            self.save_session(session)
    
    def _save_session(self, session: Session):
        """Save a new session."""
        sessions = self.list_sessions()
        sessions.append(session)
        self._save_all_sessions(sessions)
    
    def _save_all_sessions(self, sessions: List[Session]):
        """Save all sessions to file."""
        data = [session.to_dict() for session in sessions]
        self.sessions_file.write_text(json.dumps(data, indent=2))