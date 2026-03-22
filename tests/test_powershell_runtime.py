import platform

import pytest

from dais_shell import AgentShell, CommandStep, ForbiddenShellTargetError, ShellResultStatus


def _build_step(command: str, args: list[str] | None = None) -> CommandStep:
    return CommandStep(
        command=command,
        args=args or [],
        env={},
        cwd=".",
        timeout=None,
    )

def test_powershell_single_quote_escaping():
    if platform.system() != "Windows":
        pytest.skip(f"Current platform is {platform.system()}, not Windows")

    shell = AgentShell()
    result = shell.run_sync(_build_step("echo", ["Hello", "I'm Dais"]))
    assert result.status == ShellResultStatus.SUCCESS
    assert result.error is None
    assert result.returncode == 0

def test_powershell_stderr_clixml_stripped():
    if platform.system() != "Windows":
        pytest.skip(f"Current platform is {platform.system()}, not Windows")
    shell = AgentShell()

    result = shell.run_sync(_build_step("Get-Item", ["C:\\nonexistent_path_that_does_not_exist"]))
    assert result.returncode != 0
    assert "#< CLIXML" not in result.stderr
    assert "<Objs" not in result.stderr
    assert len(result.stderr.strip()) > 0
