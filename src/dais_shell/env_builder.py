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

class EnvBuilder:
    def __init__(self,
                 blacklist: set[str] | None = None,
                 extra: dict[str, str] | None = None,
                 ):
        self._blacklist = blacklist
        self._extra = extra

    def with_extra(self, extra: dict[str, str]) -> "EnvBuilder":
        final_extra = (self._extra or {}).copy()
        final_extra.update(extra)
        return EnvBuilder(self._blacklist, final_extra)

    def build(self) -> dict[str, str]:
        base_env = os.environ.copy()
        final_env = {}

        # insert essential vars
        for key, var in base_env.items():
            if key.upper() in ESSENTIAL_VARS:
                final_env[key] = var

        # insert extra vars
        if self._extra:
            final_env.update(self._extra)
        return final_env
