import platform
from typing import TypeAlias
from .env_builder import EnvBuilder
from .iostream_reader import IOStreamReaderResult, IOStreamReaderStatus
from .runtimes import BaseShellRuntime, BashRuntime, PowerShellRuntime
from .types import CommandStep
from .types.exceptions import ShellError, CommandNotFoundError, ShellRuntimeNotFoundError, ForbiddenShellTargetError
from .constants import DEFAULT_COMMAND_BLACKLIST

ShellResult: TypeAlias = IOStreamReaderResult
ShellResultStatus: TypeAlias = IOStreamReaderStatus

class AgentShell:
    def __init__(self,
                 command_blacklist: set[str] | None = None,
                 env_extra: dict[str, str] | None = None,
                 max_lines: int = 10000,
                 ):
        self._runtime = self._create_runtime(max_lines)
        self._command_blacklist = command_blacklist or DEFAULT_COMMAND_BLACKLIST
        self._env_builder = EnvBuilder(blacklist=None, extra=env_extra)

    @staticmethod
    def _create_runtime(max_lines: int) -> BaseShellRuntime:
        if platform.system() == "Windows":
            return PowerShellRuntime(max_lines)
        else:
            return BashRuntime(max_lines)

    def run_sync(self,
                 step: CommandStep,
                 on_stdout=None,
                 on_stderr=None
                 ) -> ShellResult:
        step.validate_command(self._command_blacklist)
        step.env = (self._env_builder
                        .with_extra(step.env or {})
                        .build())
        return self._runtime.run_sync(step, on_stdout, on_stderr)

    async def run(self,
                  step: CommandStep,
                  on_stdout=None,
                  on_stderr=None
                  ) -> ShellResult:
        step.validate_command(self._command_blacklist)
        step.env = (self._env_builder
                        .with_extra(step.env or {})
                        .build())
        return await self._runtime.run(step, on_stdout, on_stderr)

__all__ = [
    "AgentShell",
    "CommandStep",
    "ShellResult",
    "ShellResultStatus",

    "ShellError",
    "CommandNotFoundError",
    "ShellRuntimeNotFoundError",
    "ForbiddenShellTargetError",
]
