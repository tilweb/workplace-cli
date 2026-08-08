from __future__ import annotations

import tomllib

import pytest

from vibe.cli import mcp_cli
from vibe.core.config._settings import MCPStreamableHttp
from vibe.core.config.harness_files import init_harness_files_manager
from vibe.core.paths import VIBE_HOME


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKPLACE_HOME", str(tmp_path))
    monkeypatch.setenv("ADACOR_AI_API_KEY", "dummy-for-test")
    monkeypatch.chdir(tmp_path)  # no project .workplace -> writes to user config
    init_harness_files_manager("user", "project")
    return tmp_path


def _config_names(home):
    cfg = VIBE_HOME.path / "config.toml"
    data = tomllib.loads(cfg.read_text())
    return [s["name"] for s in data.get("mcp_servers", [])]


def test_add_http_server_writes_valid_entry(home):
    mcp_cli.run_mcp_cli([
        "add",
        "youtrack",
        "--transport",
        "streamable-http",
        "--url",
        "https://adacor.youtrack.cloud/mcp",
        "--api-key-env",
        "YOUTRACK_TOKEN",
    ])
    servers = mcp_cli.configured_servers()
    assert [s["name"] for s in servers] == ["youtrack"]
    yt = servers[0]
    assert yt["transport"] == "streamable-http"
    assert yt["url"] == "https://adacor.youtrack.cloud/mcp"
    assert yt["api_key_env"] == "YOUTRACK_TOKEN"


def test_add_stdio_server(home):
    mcp_cli.run_mcp_cli([
        "add",
        "fetch",
        "--transport",
        "stdio",
        "--",
        "uvx",
        "mcp-server-fetch",
    ])
    server = mcp_cli.configured_servers()[0]
    assert server["command"] == "uvx"
    assert server["args"] == ["mcp-server-fetch"]


def test_duplicate_without_force_exits(home):
    mcp_cli.run_mcp_cli(["add", "s", "--url", "https://a/mcp"])
    with pytest.raises(SystemExit) as exc:
        mcp_cli.run_mcp_cli(["add", "s", "--url", "https://b/mcp"])
    assert exc.value.code == 1
    assert mcp_cli.configured_servers()[0]["url"] == "https://a/mcp"


def test_force_replaces(home):
    mcp_cli.run_mcp_cli(["add", "s", "--url", "https://a/mcp"])
    mcp_cli.run_mcp_cli([
        "add",
        "s",
        "--force",
        "--transport",
        "http",
        "--url",
        "https://b/mcp",
    ])
    server = mcp_cli.configured_servers()[0]
    assert server["transport"] == "http"
    assert server["url"] == "https://b/mcp"


def test_remove(home):
    mcp_cli.run_mcp_cli(["add", "a", "--url", "https://a/mcp"])
    mcp_cli.run_mcp_cli(["add", "b", "--url", "https://b/mcp"])
    mcp_cli.run_mcp_cli(["remove", "a"])
    assert _config_names(home) == ["b"]


def test_remove_missing_exits(home):
    with pytest.raises(SystemExit) as exc:
        mcp_cli.run_mcp_cli(["remove", "ghost"])
    assert exc.value.code == 1


def test_http_without_url_is_error():
    with pytest.raises(mcp_cli.McpCliError):
        mcp_cli.build_server(
            name="x",
            transport="http",
            url=None,
            api_key_env="",
            api_key_header="Authorization",
            api_key_format="Bearer {token}",
            headers={},
            env={},
            command_argv=[],
        )


def test_stdio_without_command_is_error():
    with pytest.raises(mcp_cli.McpCliError):
        mcp_cli.build_server(
            name="x",
            transport="stdio",
            url=None,
            api_key_env="",
            api_key_header="Authorization",
            api_key_format="Bearer {token}",
            headers={},
            env={},
            command_argv=[],
        )


def test_config_stays_loadable_by_app(home):
    mcp_cli.run_mcp_cli([
        "add",
        "youtrack",
        "--url",
        "https://adacor.youtrack.cloud/mcp",
        "--api-key-env",
        "YOUTRACK_TOKEN",
    ])
    from vibe.core.config import VibeConfig

    cfg = VibeConfig.load()
    assert [s.name for s in cfg.mcp_servers] == ["youtrack"]
    assert isinstance(cfg.mcp_servers[0], MCPStreamableHttp)
