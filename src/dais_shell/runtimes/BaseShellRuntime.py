from abc import ABC, abstractmethod
from ..types.command_step import CommandStep
from ..types.shell_script import ShellScript
from ..iostream_reader import IOStreamReaderResult


class BaseShellRuntime(ABC):
    @abstractmethod
    def run_sync(self,
                 step: CommandStep | ShellScript,
                 on_stdout=None,
                 on_stderr=None,
                 ) -> IOStreamReaderResult: ...

    @abstractmethod
    async def run(self,
                  step: CommandStep | ShellScript,
                  on_stdout=None,
                  on_stderr=None
                  ) -> IOStreamReaderResult: ...
