from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Session:
    id: UUID
    created_at: datetime
    metadata: dict[str, str]
