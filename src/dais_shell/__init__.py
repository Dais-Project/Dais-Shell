import platform
from .env_builder import EnvBuilder
from .iostream_reader import IOStreamReaderResult
from .runtimes import BaseShellRuntime, BashRuntime, PowerShellRuntime
from .types import CommandStep
from .constants import DEFAULT_COMMAND_BLACKLIST

class AgentShell:
    def __init__(self,
                 command_blacklist: set[str] | None = None,
                 env_extra: dict[str, str] | None = None,
                 ):
        self._runtime = self._detect_runtime()
        self._command_blacklist = command_blacklist or DEFAULT_COMMAND_BLACKLIST
        self._env_builder = EnvBuilder(blacklist=None, extra=env_extra)

    @staticmethod
    def _detect_runtime() -> BaseShellRuntime:
        if platform.system() == "Windows":
            return PowerShellRuntime()
        else:
            return BashRuntime()

    def run_sync(self,
                 step: CommandStep,
                 on_stdout=None,
                 on_stderr=None
                 ) -> IOStreamReaderResult:
        step.validate_command(self._command_blacklist)
        step.env = (self._env_builder
                        .with_extra(step.env or {})
                        .build())
        return self._runtime.run_sync(step, on_stdout, on_stderr)
