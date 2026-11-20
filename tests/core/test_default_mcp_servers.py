from __future__ import annotations

from vibe.cli.mcp_cli import configured_servers
from vibe.core.config import VibeConfig


def test_youtrack_default_injected_when_token_present(monkeypatch):
    monkeypatch.setenv("YOUTRACK_TOKEN", "perm-dummy")
    cfg = VibeConfig.load()
    names = [s.name for s in cfg.mcp_servers]
    assert names.count("youtrack") == 1
    youtrack = next(s for s in cfg.mcp_servers if s.name == "youtrack")
    assert youtrack.url == "https://adacor.youtrack.cloud/mcp"
    assert youtrack.api_key_env == "YOUTRACK_TOKEN"


def test_not_injected_without_token(monkeypatch):
    monkeypatch.delenv("YOUTRACK_TOKEN", raising=False)
    cfg = VibeConfig.load()
    assert "youtrack" not in [s.name for s in cfg.mcp_servers]


def test_default_is_not_persisted_to_config(monkeypatch):
    monkeypatch.setenv("YOUTRACK_TOKEN", "perm-dummy")
    VibeConfig.load()
    # The injected default is virtual — it must not be written to config.toml.
    assert "youtrack" not in [s.get("name") for s in configured_servers()]


def test_user_config_overrides_default(monkeypatch):
    monkeypatch.setenv("YOUTRACK_TOKEN", "perm-dummy")
    VibeConfig.save_updates({
        "mcp_servers": [
            {
                "name": "youtrack",
                "transport": "streamable-http",
                "url": "https://custom.example/mcp",
                "disabled": True,
            }
        ]
    })
    cfg = VibeConfig.load()
    youtrack = [s for s in cfg.mcp_servers if s.name == "youtrack"]
    assert len(youtrack) == 1  # no duplicate of the default
    assert youtrack[0].url == "https://custom.example/mcp"
    assert youtrack[0].disabled is True
