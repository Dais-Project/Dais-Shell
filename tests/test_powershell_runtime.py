import os
import platform
import time
import tempfile

import pytest

from dais_shell import AgentShell, CommandStep, ShellResultStatus


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

def test_powershell_args_empty():
    if platform.system() != "Windows":
        pytest.skip(f"Current platform is {platform.system()}, not Windows")

    shell = AgentShell()
    result = shell.run_sync(_build_step("Get-Date"))
    assert result.status == ShellResultStatus.SUCCESS
    assert result.returncode == 0
    assert result.stdout.strip() != ""

def test_dollar_sign_is_literal():
    if platform.system() != "Windows":
        pytest.skip(f"Current platform is {platform.system()}, not Windows")
    result = AgentShell().run_sync(_build_step("Write-Output", ["$HOME"]))
    assert result.returncode == 0
    assert result.stdout.strip() == "$HOME"

def test_backtick_is_literal():
    if platform.system() != "Windows":
        pytest.skip(f"Current platform is {platform.system()}, not Windows")
    result = AgentShell().run_sync(_build_step("Write-Output", ["hello`nworld"]))
    assert result.returncode == 0
    assert result.stdout.strip() == "hello`nworld"

def test_double_quote_in_arg():
    if platform.system() != "Windows":
        pytest.skip(f"Current platform is {platform.system()}, not Windows")
    result = AgentShell().run_sync(_build_step("Write-Output", ['Say "hello"']))
    assert result.returncode == 0
    assert 'Say "hello"' in result.stdout

def test_positional_args_only():
    if platform.system() != "Windows":
        pytest.skip(f"Current platform is {platform.system()}, not Windows")
    result = AgentShell().run_sync(_build_step("Write-Output", ["alpha", "beta"]))
    assert result.returncode == 0
    assert "alpha" in result.stdout
    assert "beta" in result.stdout

def test_command_not_found_returns_error():
    if platform.system() != "Windows":
        pytest.skip(f"Current platform is {platform.system()}, not Windows")
    result = AgentShell().run_sync(_build_step("NonExistentCommand_DAIS_XYZ"))
    assert result.returncode != 0

def test_cwd_is_respected():
    if platform.system() != "Windows":
        pytest.skip(f"Current platform is {platform.system()}, not Windows")
    with tempfile.TemporaryDirectory() as tmpdir:
        step = CommandStep(command="python", args=["-c", "import os; print(os.getcwd())"],
                           env={}, cwd=tmpdir, timeout=None)
        result = AgentShell().run_sync(step)
        print("location: ", result.stdout, result.stderr)
        assert result.returncode == 0
        assert os.path.normcase(tmpdir) in os.path.normcase(result.stdout)

def test_timeout_kills_process():
    if platform.system() != "Windows":
        pytest.skip(f"Current platform is {platform.system()}, not Windows")
    step = CommandStep(command="Start-Sleep", args=["-Seconds", "30"],
                       env={}, cwd=".", timeout=1)
    t0 = time.monotonic()
    result = AgentShell().run_sync(step)
    assert time.monotonic() - t0 < 10
    assert result.status != ShellResultStatus.SUCCESS

def test_on_stdout_callback_receives_output():
    if platform.system() != "Windows":
        pytest.skip(f"Current platform is {platform.system()}, not Windows")
    lines = []
    result = AgentShell().run_sync(
        _build_step("Write-Output", ["cb_line"]),
        on_stdout=lambda line: lines.append(line),
    )
    assert result.returncode == 0
    assert any("cb_line" in l for l in lines)

def test_on_stderr_callback_receives_error():
    if platform.system() != "Windows":
        pytest.skip(f"Current platform is {platform.system()}, not Windows")
    lines = []
    # Get-Item 在路径不存在时写 stderr，exitcode 非零
    result = AgentShell().run_sync(
        _build_step("Get-Item", ["C:\\nonexistent_dais_xyz"]),
        on_stderr=lambda line: lines.append(line),
    )
    assert result.returncode != 0
    assert len(lines) > 0

# -- specific command tests --

def test_remove_item_with_force_flag():
    if platform.system() != "Windows":
        pytest.skip(f"Current platform is {platform.system()}, not Windows")

    fd, tmp_path = tempfile.mkstemp(suffix=".txt", prefix="dais_test_")
    os.close(fd)

    try:
        assert os.path.exists(tmp_path)

        shell = AgentShell()
        step = CommandStep(
            command="Remove-Item",
            args=["-Path", tmp_path, "-Force"],
            env={},
            cwd=".",
            timeout=None,
        )
        result = shell.run_sync(step)

        assert result.status == ShellResultStatus.SUCCESS
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert not os.path.exists(tmp_path), f"File should have been deleted: {tmp_path}"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
