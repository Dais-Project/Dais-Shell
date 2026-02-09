import asyncio
import shutil
import subprocess
from dataclasses import dataclass
from .BaseShellRuntime import BaseShellRuntime
from ..types import CommandStep
from ..types.exceptions import ShellRuntimeNotFoundError
from ..iostream_reader import IOStreamReaderResult, IOStreamReader, IOStreamReaderSync

@dataclass
class BashCommandStep(CommandStep):
    @classmethod
    def from_command_step(cls, step: CommandStep):
        return cls(
            command=step.command,
            args=step.args,
            env=step.env,
            cwd=step.cwd,
            timeout=step.timeout
        )

    def to_wrapper_script(self):
        return 'exec "$1" "${@:2}"'

# --- --- --- --- --- ---

class BashRuntime(BaseShellRuntime):
    def __init__(self, max_lines: int):
        self._shell = self._detect_shell()
        self._max_lines = max_lines

    def _detect_shell(self) -> str:
        if bash := shutil.which("bash"):
            return bash
        if sh := shutil.which("sh"):
            return sh
        raise ShellRuntimeNotFoundError("Bash")

    def _make_bash_commands(self, step: BashCommandStep):
        return [
            self._shell,
            "-c",
            step.to_wrapper_script(),
            "--",
            step.command,
            *step.args
        ]

    def _prepare_cmd(self, step: CommandStep) -> list[str]:
        step = BashCommandStep.from_command_step(step)
        resolved = shutil.which(step.command)
        is_shell_command = resolved is None
        if is_shell_command:
            return self._make_bash_commands(step)
        else:
            return [resolved, *step.args]

    def run_sync(self,
                 step: CommandStep,
                 on_stdout=None,
                 on_stderr=None,
                ) -> IOStreamReaderResult:
        proc = subprocess.Popen(
            self._prepare_cmd(step),
            cwd=step.cwd,
            env=step.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        reader = IOStreamReaderSync(proc, on_stdout, on_stderr, self._max_lines)
        return reader.read(step.timeout)

    async def run(self,
                        step: CommandStep,
                        on_stdout=None,
                        on_stderr=None
                        ) -> IOStreamReaderResult:
        proc = await asyncio.create_subprocess_exec(
            *self._prepare_cmd(step),
            cwd=step.cwd,
            env=step.env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        reader = IOStreamReader(proc, self._max_lines, on_stdout, on_stderr)
        return await reader.read(step.timeout)
