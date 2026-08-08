from dataclasses import dataclass
from pathlib import Path


@dataclass
class ShellScript:
    """Trusted shell source executed directly without command blacklist validation."""

    script: str
    cwd: str | Path
    env: dict[str, str] | None = None
    timeout: int | None = None


__all__ = [
    "ShellScript",
]
