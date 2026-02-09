from abc import ABC, abstractmethod
from ..types import CommandStep
from ..iostream_reader import IOStreamReaderResult

class BaseShellRuntime(ABC):
    @abstractmethod
    def run_sync(self,
                 step: CommandStep,
                 on_stdout=None,
                 on_stderr=None,
                 ) -> IOStreamReaderResult: ...

    @abstractmethod
    async def run(self,
                  step: CommandStep,
                  on_stdout=None,
                  on_stderr=None
                  ) -> IOStreamReaderResult: ...
