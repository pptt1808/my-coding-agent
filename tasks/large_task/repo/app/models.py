from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Optional


class Status(str, Enum):
    OPEN = "open"
    DONE = "done"


@dataclass
class Task:
    id: int
    title: str
    status: Status = Status.OPEN
    priority: int = 1  # 1 low, 2 medium, 3 high

    def to_dict(self):
        return asdict(self)
