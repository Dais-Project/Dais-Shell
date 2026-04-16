from string import Template


class EnvExpander:
    def __init__(self, env: dict[str, str]):
        self._env = env

    def expand(self, arg: str) -> str:
        return Template(arg).safe_substitute(self._env)
