from datetime import datetime, timezone
from uuid import UUID, uuid4

from back.domain.models import Session, Task


class FrontendInteractionService:
    def __init__(self) -> None:
        self._sessions: dict[UUID, Session] = {}
        self._tasks: dict[UUID, Task] = {}

    async def start_session(self, metadata: dict[str, str]) -> Session:
        if not isinstance(metadata, dict):
            raise TypeError("Session metadata must be a dictionary")

        created_at = datetime.now(timezone.utc)
        session = Session(id=uuid4(), created_at=created_at, metadata=metadata)
        self._sessions[session.id] = session
        return session

    async def start_task(self, session_id: UUID, payload: dict[str, object]) -> Task:
        if session_id not in self._sessions:
            raise ValueError("Session must exist before starting a task")
        if not isinstance(payload, dict):
            raise TypeError("Task payload must be a dictionary")

        created_at = datetime.now(timezone.utc)
        task = Task(id=uuid4(), session_id=session_id, created_at=created_at, payload=payload)
        self._tasks[task.id] = task
        return task
