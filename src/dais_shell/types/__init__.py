import os
import shutil
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from .exceptions import CommandNotFoundError, ForbiddenShellTargetError

@dataclass
class CommandStep:
    command: str
    args: list[str]
    cwd: str | Path
    env: dict[str, str] | None = None
    timeout: int | None = None

    @abstractmethod
    def to_wrapper_script(self) -> str: ...

    def validate_command(self, filter: set[str] | None = None):
        if filter is not None:
            name = os.path.basename(self.command).lower()
            if name in filter:
                raise ForbiddenShellTargetError(name)
        resolved = shutil.which(self.command)
        if resolved is None:
            raise CommandNotFoundError(self.command)
