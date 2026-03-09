import asyncio

from dais_shell import AgentShell, CommandStep


def _build_step() -> CommandStep:
    return CommandStep(
        command="echo",
        args=["Hello World"],
        env={},
        cwd=".",
        timeout=None,
    )


def test_helloworld_sync() -> None:
    shell = AgentShell()
    result = shell.run_sync(_build_step())

    assert result.stdout.strip() == "Hello World"
    assert result.stderr == ""
    assert result.error is None
    assert result.returncode == 0


def test_helloworld_async() -> None:
    shell = AgentShell()

    async def _run():
        return await shell.run(_build_step())

    result = asyncio.run(_run())

    assert result.stdout.strip() == "Hello World"
    assert result.stderr == ""
    assert result.error is None
    assert result.returncode == 0
