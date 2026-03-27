import os
import platform

import dais_shell.env_builder as env_builder_module
from dais_shell.env_builder import ESSENTIAL_VARS, EnvBuilder


def _patch_environ(monkeypatch, env: dict[str, str]):
    monkeypatch.setattr(env_builder_module.os, "environ", env.copy())


def test_with_extra_returns_new_builder_and_overrides_keys(monkeypatch):
    _patch_environ(monkeypatch, {})

    builder = EnvBuilder(extra={"A": "1", "B": "1"})
    new_builder = builder.with_extra({"B": "2", "C": "3"})

    assert new_builder is not builder
    assert builder.build() == {"A": "1", "B": "1"}
    assert new_builder.build() == {"A": "1", "B": "2", "C": "3"}


def test_with_paths_returns_new_builder_and_appends_paths_in_order(monkeypatch):
    _patch_environ(monkeypatch, {})

    builder = EnvBuilder(extra_paths=["path0"])
    new_builder = builder.with_paths(["path1", "path2"]).with_paths(["path3"])

    assert builder.build()["PATH"] == "path0"
    assert new_builder.build()["PATH"] == os.pathsep.join(["path0", "path1", "path2", "path3"])


def test_build_keeps_only_essential_vars_and_injects_extra(monkeypatch):
    _patch_environ(
        monkeypatch,
        {
            "PATH": "base_path",
            "TMP": "temp_path",
            "NOT_ESSENTIAL": "should_not_exist",
        },
    )

    builder = EnvBuilder(extra={"CUSTOM_VAR": "custom_value"})
    final_env = builder.build()

    assert final_env["PATH"] == "base_path"
    assert final_env["TMP"] == "temp_path"
    assert final_env["CUSTOM_VAR"] == "custom_value"
    assert "NOT_ESSENTIAL" not in final_env


def test_blacklist_filters_keys_case_insensitively_for_env_key(monkeypatch):
    _patch_environ(
        monkeypatch,
        {
            "PaTh": "base_path",
            "TMP": "temp_path",
        },
    )

    builder = EnvBuilder(blacklist={"PATH"})
    final_env = builder.build()

    assert "PaTh" not in final_env
    assert final_env["TMP"] == "temp_path"


def test_build_prepends_extra_paths_before_existing_path(monkeypatch):
    _patch_environ(monkeypatch, {"PATH": "base_path"})

    builder = EnvBuilder(extra_paths=["extra1", "extra2"])
    final_env = builder.build()

    assert final_env["PATH"] == os.pathsep.join(["extra1", "extra2", "base_path"])


def test_build_uses_extra_paths_when_existing_path_missing(monkeypatch):
    _patch_environ(monkeypatch, {"TMP": "temp_path"})

    builder = EnvBuilder(extra_paths=["extra1", "extra2"])
    final_env = builder.build()

    assert final_env["PATH"] == os.pathsep.join(["extra1", "extra2"])


def test_essential_vars_are_uppercase_and_include_path():
    assert isinstance(ESSENTIAL_VARS, frozenset)
    assert "PATH" in ESSENTIAL_VARS
    assert all(key == key.upper() for key in ESSENTIAL_VARS)


def test_essential_vars_include_platform_specific_markers():
    system = platform.system()

    if system == "Windows":
        assert "SYSTEMROOT" in ESSENTIAL_VARS
        assert "DYLD_LIBRARY_PATH" not in ESSENTIAL_VARS
    elif system == "Darwin":
        assert "HOME" in ESSENTIAL_VARS
        assert "DYLD_LIBRARY_PATH" in ESSENTIAL_VARS
        assert "SYSTEMROOT" not in ESSENTIAL_VARS
    else:
        assert "HOME" in ESSENTIAL_VARS
        assert "DYLD_LIBRARY_PATH" not in ESSENTIAL_VARS
        assert "SYSTEMROOT" not in ESSENTIAL_VARS
