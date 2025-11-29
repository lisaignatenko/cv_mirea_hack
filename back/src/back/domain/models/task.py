from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Task:
    id: UUID
    session_id: UUID
    created_at: datetime
    payload: dict[str, object]
