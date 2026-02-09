class ShellError(Exception): ...

class CommandNotFoundError(ShellError):
    def __init__(self, command: str):
        self.command = command
        super().__init__(f"Command not found: {command}")

class ShellRuntimeNotFoundError(ShellError):
    def __init__(self, runtime: str):
        self.runtime = runtime
        super().__init__(f"Shell runtime not found: {runtime}")

class ForbiddenShellTargetError(ShellError):
    def __init__(self, command: str):
        self.command = command
        super().__init__(f"Refusing to execute shell program as target: {command}")

class ExecutionTimeoutError(ShellError): ...

