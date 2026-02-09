import asyncio
import base64
import os
import json
import shutil
import subprocess
from dataclasses import dataclass
from .BaseShellRuntime import BaseShellRuntime
from ..iostream_reader import IOStreamReaderResult, IOStreamReader, IOStreamReaderSync
from ..types import CommandStep
from ..types.exceptions import ShellRuntimeNotFoundError

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

@dataclass
class PowerShellCommandStep(CommandStep):
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
        cmd_json  = json.dumps(self.command)
        args_json = json.dumps(self.args)
        script = f"""
$ErrorActionPreference = "Stop"
$PSNativeCommandArgumentPassing = "Standard"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$command  = ConvertFrom-Json '{cmd_json}'
$arguments = ,(ConvertFrom-Json '{args_json}')

& $command @arguments
exit $LASTEXITCODE"""
        return script.strip()

# --- --- --- --- --- ---

class PowerShellRuntime(BaseShellRuntime):
    def __init__(self, max_lines: int):
        self._shell = self._detect_shell()
        self._max_lines = max_lines

    @staticmethod
    def _detect_shell() -> str:
        if pwsh := shutil.which("pwsh"):
            return pwsh
        if powershell := shutil.which("powershell"):
            return powershell
        raise ShellRuntimeNotFoundError("PowerShell")

    @staticmethod
    def _encode(source: str) -> str:
        return base64.b64encode(
            source.encode("utf-16-le")
        ).decode("ascii")

    def _make_powershell_commands(self, encoded: str):
        return [
            self._shell,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-EncodedCommand", encoded
        ]

    def _prepare_cmd(self, step: CommandStep) -> list[str]:
        step = PowerShellCommandStep.from_command_step(step)
        script = step.to_wrapper_script()
        encoded = self._encode(script)
        return self._make_powershell_commands(encoded)

    def run_sync(
        self,
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
            creationflags=CREATE_NO_WINDOW
        )

        reader = IOStreamReaderSync(proc, on_stdout, on_stderr, self._max_lines)
        return reader.read(step.timeout)

    async def run(
        self,
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
            creationflags=CREATE_NO_WINDOW
        )

        reader = IOStreamReader(proc, self._max_lines, on_stdout, on_stderr)
        return await reader.read(step.timeout)
