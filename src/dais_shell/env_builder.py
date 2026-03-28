import os
import platform


WINDOWS_ESSENTIAL_VARS = {
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "PATHEXT",
    "COMSPEC",
    "WINDIR",

    "USERPROFILE",
    "USERNAME",
    "COMPUTERNAME",
    "APPDATA",
    "LOCALAPPDATA",
    "PUBLIC",

    "PROCESSOR_ARCHITECTURE"
}

UNIX_ESSENTIAL_VARS = {
    "HOME",
    "USER",
    "LOGNAME",
    "SHELL",
    "TERM",
    "LINES", "COLUMNS",
    "PWD",
    "XDG_RUNTIME_DIR", "XDG_CONFIG_HOME"
}

MACOS_ESSENTIAL_VARS = UNIX_ESSENTIAL_VARS | {
    "DYLD_LIBRARY_PATH",
    "DYLD_FRAMEWORK_PATH",
    "DYLD_FALLBACK_LIBRARY_PATH",

    "SSH_AUTH_SOCK",
    "SECURITYSESSIONID",

    "__CF_USER_TEXT_ENCODING",
    "DEVELOPER_DIR",

    "TERM_PROGRAM",
    "TERM_PROGRAM_VERSION",
}

UNIVERSAL_ESSENTIAL_VARS = {
    "PATH",
    "TEMP", "TMP", "TMPDIR",
    "LANG", "LC_ALL", "LC_CTYPE",
}

PROGRAM_ESSENTIAL_VARS = {
    "PYTHONIOENCODING",
    "GOPATH",
    "LUA_PATH",
    "JAVA_HOME",
    "RUSTUP_HOME",
    "CARGO_HOME",
    "PNPM_HOME",
    "ANDROID_HOME"
}

SECURITY_ADDITIONS = {
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "REQUESTS_CA_BUNDLE"
}

ESSENTIAL_VARS = UNIVERSAL_ESSENTIAL_VARS | PROGRAM_ESSENTIAL_VARS | SECURITY_ADDITIONS
if platform.system() == "Windows":
    ESSENTIAL_VARS |= WINDOWS_ESSENTIAL_VARS
elif platform.system() == "Darwin":
    ESSENTIAL_VARS |= MACOS_ESSENTIAL_VARS
else:
    ESSENTIAL_VARS |= UNIX_ESSENTIAL_VARS

# Ensure all vars in ESSENTIAL_VARS uppercase
ESSENTIAL_VARS = frozenset(v.upper() for v in ESSENTIAL_VARS)


CONSTANT_VARS = {
    "PYTHONUTF8": "1",
    "PYTHONIOENCODING": "utf-8",
    "JAVA_TOOL_OPTIONS": "-Dfile.encoding=UTF-8",
    "RUBYOPT": "-EUTF-8",
}

class EnvBuilder:
    def __init__(self,
                 blacklist: set[str] | None = None,
                 extra: dict[str, str] | None = None,
                 extra_paths: list[str] | None = None,
                 ):
        self._blacklist = blacklist
        self._extra = extra or {}
        self._extra_paths = extra_paths or []

    def with_extra(self, extra: dict[str, str]) -> "EnvBuilder":
        return EnvBuilder(
            blacklist=self._blacklist,
            extra={**self._extra, **extra},
            extra_paths=self._extra_paths,
        )

    def with_paths(self, paths: list[str]) -> "EnvBuilder":
        return EnvBuilder(
            blacklist=self._blacklist,
            extra=self._extra,
            extra_paths=self._extra_paths + paths,
        )

    def build(self) -> dict[str, str]:
        base_env = os.environ.copy()
        final_env = CONSTANT_VARS.copy()

        for key, var in base_env.items():
            # skip blacklisted vars
            if self._blacklist and key.upper() in self._blacklist:
                continue
            # insert essential vars
            if key.upper() in ESSENTIAL_VARS:
                final_env[key] = var

        # insert extra vars
        final_env.update(self._extra)

        # insert extra paths
        if len(self._extra_paths) > 0:
            parts = self._extra_paths.copy()
            existing = final_env.get("PATH", None)
            if existing: parts.append(existing)
            final_env["PATH"] = os.pathsep.join(parts)
        return final_env
