import asyncio
import base64
import json
import shutil
import re
import xml.etree.ElementTree as ET
import subprocess
from dataclasses import dataclass
from .BaseShellRuntime import BaseShellRuntime
from ..iostream_reader import IOStreamReader, IOStreamReaderResult
from ..types import CommandStep, ShellRuntimeNotFoundError


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
        def ps_encode(s: str) -> str:
            return base64.b64encode(s.encode("utf-8")).decode("ascii")

        cmd_json  = json.dumps(self.command)
        args_json = json.dumps(self.args)

        if len(self.args) > 0:
            # encode to base64 and decode in script to prevent single quotes in the args
            args_b64 = ps_encode(args_json)
            args_line = f"""\
            $args_json = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{args_b64}'))
            $arguments = ,(ConvertFrom-Json $args_json)
            """
            invoke_line = "& $command @arguments"
        else:
            # when no arguments, PowerShell ConvertFrom-Json will parse as null
            # which will cause error for some commands.
            args_line = ""
            invoke_line = "& $command"

        script = f"""
$ErrorActionPreference = "Stop"
$PSNativeCommandArgumentPassing = "Standard"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$command  = ConvertFrom-Json '{cmd_json}'
{args_line}

{invoke_line}
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
        # powershell `-EncodedCommand` receives UTF-16-LE encoded string
        return base64.b64encode(
            source.encode("utf-16-le")
        ).decode("ascii")

    @staticmethod
    def _strip_clixml(text: str) -> str:
        """
        Powershell outputs CLIXML when its stderr is connected to a pipe,
        so we need to strip the original text from the stderr.
        """
        if not text.strip().startswith("#< CLIXML"):
            return text

        xml_part = text.strip()[len("#< CLIXML"):].strip()
        try:
            root = ET.fromstring(xml_part)
            ns = {"ps": "http://schemas.microsoft.com/powershell/2004/04"}
            parts = []
            for s in root.findall(".//ps:S", ns):
                if not s.text:
                    continue
                t = s.text
                # PowerShell 用 _xNNNN_ 编码特殊字符（包括 ANSI escape \x1b = _x001B_）
                t = re.sub(
                    r"_x([0-9A-Fa-f]{4})_",
                    lambda m: chr(int(m.group(1), 16)),
                    t
                )
                # 剥掉 ANSI 颜色码
                t = re.sub(r"\x1b\[[0-9;]*m", "", t)
                parts.append(t)
            return "".join(parts)
        except ET.ParseError:
            # returns the raw text as fallback
            return text

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
        return asyncio.run(self.run(step, on_stdout, on_stderr))

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
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        )

        reader = IOStreamReader(proc, self._max_lines, on_stdout, on_stderr)
        read_result = await reader.read(step.timeout)
        cleaned_stderr = self._strip_clixml(read_result.stderr)
        read_result.stderr_buf.clear()
        read_result.stderr_buf.extend(cleaned_stderr.splitlines())
        return read_result
