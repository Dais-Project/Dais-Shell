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


def test_command_blacklist_blocks_target() -> None:
    shell = AgentShell(command_blacklist={"echo"})

    with pytest.raises(ForbiddenShellTargetError):
        shell.run_sync(_build_step("echo", ["blocked"]))


@pytest.mark.parametrize(
    ("system_name", "builtin_command"),
    [
        ("Windows", "Get-Location"),
        ("Linux", "pwd"),
        ("Darwin", "pwd"),
    ],
)
def test_shell_builtin_command_executes_successfully(system_name: str, builtin_command: str) -> None:
    if platform.system() != system_name:
        pytest.skip(f"Current platform is {platform.system()}, not {system_name}")

    shell = AgentShell()
    result = shell.run_sync(_build_step(builtin_command))

    assert result.status == ShellResultStatus.SUCCESS
    assert result.error is None
    assert result.returncode == 0


def test_nonexistent_command_returns_nonzero() -> None:
    shell = AgentShell()
    result = shell.run_sync(_build_step("__dais_command_should_not_exist__"))

    assert result.status == ShellResultStatus.SUCCESS
    assert result.returncode != 0
