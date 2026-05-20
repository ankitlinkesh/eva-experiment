from __future__ import annotations

from secrets import token_hex


class DeviceSessions:
    def __init__(self) -> None:
        self._sessions: set[str] = set()

    def create(self) -> str:
        session = token_hex(18)
        self._sessions.add(session)
        return session

    def validate(self, session: str) -> bool:
        return session in self._sessions
