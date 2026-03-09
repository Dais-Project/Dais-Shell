import os
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from .exceptions import ForbiddenShellTargetError

@dataclass
class CommandStep:
    command: str
    args: list[str]
    cwd: str | Path
    env: dict[str, str] | None = None
    timeout: int | None = None

    @abstractmethod
    def to_wrapper_script(self) -> str: ...

    def validate_forbidden(self, filter: set[str] | None = None):
        if filter is not None:
            name = os.path.basename(self.command).lower()
            if name in filter:
                raise ForbiddenShellTargetError(name)

__all__ = [
    "CommandStep",
]
