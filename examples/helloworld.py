from dais_shell import AgentShell, CommandStep

shell = AgentShell()

step = CommandStep(
    command="echo",
    args=["Hello World"],
    env={},
    cwd=".",
    timeout=None
)

result = shell.run_sync(step)

print("stdout buffer: ", result.stdout_buf)
print("stderr buffer: ", result.stderr_buf)
print("stdout: ", result.stdout)
print("stderr: ", result.stderr)
print("returncode: ", result.returncode)
print("status: ", result.status)
