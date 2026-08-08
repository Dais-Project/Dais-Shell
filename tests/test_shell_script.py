import platform

import pytest

from dais_shell import (
    AgentShell,
    CommandStep,
    ForbiddenShellTargetError,
    ShellResultStatus,
    ShellScript,
)


def _script(source: str, cwd=".") -> ShellScript:
    return ShellScript(
        script=source,
        cwd=cwd,
        env={},
        timeout=None,
    )


def test_shell_script_pipeline_executes_as_complete_script():
    if platform.system() == "Windows":
        source = "'hello' | ForEach-Object { $_.ToUpperInvariant() }"
    else:
        source = "printf 'hello\\n' | tr '[:lower:]' '[:upper:]'"

    result = AgentShell().run_sync(_script(source))

    assert result.status == ShellResultStatus.SUCCESS
    assert result.returncode == 0
    assert result.stdout == "HELLO"


def test_shell_script_redirects_stdout_to_file(tmp_path):
    output_path = tmp_path / "output.txt"
    if platform.system() == "Windows":
        escaped_path = str(output_path).replace("'", "''")
        source = f"'redirected' | Set-Content -Encoding utf8 '{escaped_path}'"
    else:
        escaped_path = str(output_path).replace("'", "'\\''")
        source = f"printf 'redirected\\n' > '{escaped_path}'"

    result = AgentShell().run_sync(_script(source, cwd=tmp_path))

    assert result.status == ShellResultStatus.SUCCESS
    assert result.returncode == 0
    assert result.stdout == ""
    assert output_path.read_text(encoding="utf-8-sig").strip() == "redirected"


def test_shell_script_preserves_explicit_exit_code():
    source = "exit 7"

    result = AgentShell().run_sync(_script(source))

    assert result.status == ShellResultStatus.SUCCESS
    assert result.returncode == 7


def test_shell_script_preserves_native_command_exit_code():
    source = 'python -c "import sys; sys.exit(7)"'

    result = AgentShell().run_sync(_script(source))

    assert result.status == ShellResultStatus.SUCCESS
    assert result.returncode == 7


def test_shell_script_outputs_unicode():
    expected = "你好世界 🎉"
    if platform.system() == "Windows":
        source = f"[Console]::WriteLine('{expected}')"
    else:
        source = f"printf '{expected}\\n'"

    result = AgentShell().run_sync(_script(source))

    assert result.status == ShellResultStatus.SUCCESS
    assert result.returncode == 0
    assert result.stdout == expected


def test_shell_script_returns_nonzero_for_powershell_error():
    if platform.system() != "Windows":
        pytest.skip("PowerShell-specific behavior")

    result = AgentShell().run_sync(_script("Write-Error 'boom'"))

    assert result.status == ShellResultStatus.SUCCESS
    assert result.returncode != 0
    assert "boom" in result.stderr


def test_shell_script_uses_final_powershell_command_status():
    if platform.system() != "Windows":
        pytest.skip("PowerShell-specific behavior")

    source = 'python -c "import sys; sys.exit(7)"\nWrite-Output "recovered"'
    result = AgentShell().run_sync(_script(source))

    assert result.status == ShellResultStatus.SUCCESS
    assert result.returncode == 0
    assert result.stdout == "recovered"


def test_command_step_blacklist_still_applies():
    shell = AgentShell(command_blacklist={"echo"})
    step = CommandStep(command="echo", args="blocked", cwd=".", env={})

    with pytest.raises(ForbiddenShellTargetError):
        shell.run_sync(step)
