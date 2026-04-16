import platform
import sys
import time

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


def test_command_blacklist_blocks_target():
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
def test_shell_builtin_command_executes_successfully(system_name: str, builtin_command: str):
    if platform.system() != system_name:
        pytest.skip(f"Current platform is {platform.system()}, not {system_name}")

    shell = AgentShell()
    result = shell.run_sync(_build_step(builtin_command))

    assert result.status == ShellResultStatus.SUCCESS
    assert result.error is None
    assert result.returncode == 0


def test_nonexistent_command_returns_nonzero():
    shell = AgentShell()
    result = shell.run_sync(_build_step("__dais_command_should_not_exist__"))

    assert result.status == ShellResultStatus.SUCCESS
    assert result.returncode != 0


def test_multiline_output():
    shell = AgentShell()
    result = shell.run_sync(_build_step("python", ["-c", "for i in range(5): print(i * 10)"]))

    assert list(result.stdout_buf) == [
        "0",
        "10",
        "20",
        "30",
        "40",
    ]


@pytest.mark.parametrize(
    ("system_name", "command", "args"),
    [
        ("Windows", "ping", ["-n", "10", "127.0.0.1"]),
        ("Linux", "sleep", ["10"]),
        ("Darwin", "sleep", ["10"]),
    ],
)
def test_command_timeout_interrupts_process(system_name: str, command: str, args: list[str]):
    if platform.system() != system_name:
        pytest.skip(f"Current platform is {platform.system()}, not {system_name}")

    shell = AgentShell()
    step = CommandStep(
        command=command,
        args=args,
        env={},
        cwd=".",
        timeout=1,
    )

    start_time = time.monotonic()
    result = shell.run_sync(step)
    end_time = time.monotonic()

    assert (end_time - start_time) < 2

    assert result.status == ShellResultStatus.TIMEOUT
    assert result.error is None
    if sys.platform == "win32":
        assert result.returncode != 0
    else:
        assert result.returncode == -9


class TestEnvVariables:
    def test_agent_shell_extra_env_passed_to_command(self):
        expected_value = "extra_env_value"
        shell = AgentShell(extra_env={"EXTRA_VAR": expected_value})

        step = CommandStep(
            command="echo",
            args=["$EXTRA_VAR"],
            cwd=".",
            env={},
        )
        result = shell.run_sync(step)

        assert result.status == ShellResultStatus.SUCCESS
        assert result.returncode == 0
        assert result.stdout == expected_value


class TestOutputEncoding:
    UNICODE_SAMPLES = [
        "你好世界",
        "日本語テスト",
        "한국어 테스트",
        "Ünïcödé",
        "emoji: 🎉🔥",
    ]

    @pytest.mark.parametrize("text", UNICODE_SAMPLES)
    def test_python_output_encoding(self, text):
         shell = AgentShell()
         step = _build_step("python", ["-c", f"print('{text}')"])
         result = shell.run_sync(step)
         assert result.stdout == text

    @pytest.mark.parametrize("text", UNICODE_SAMPLES)
    def test_node_output_encoding(self, text):
         shell = AgentShell()
         step = _build_step("node", ["-e", f"console.log('{text}')"])
         result = shell.run_sync(step)
         assert result.stdout == text
