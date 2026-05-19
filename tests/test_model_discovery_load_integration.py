"""Integration test: VibeConfig.load() merges the discovery cache."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from vibe.core.config import VibeConfig
from vibe.core.config._settings import DEFAULT_ACTIVE_MODEL
from vibe.core.llm.model_discovery import CACHE_VERSION, get_cache_path


def _write_cache(providers: dict[str, dict]) -> Path:
    target = get_cache_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"version": CACHE_VERSION, "providers": providers}), encoding="utf-8"
    )
    return target


def test_load_merges_cache_providers_and_models() -> None:
    _write_cache(
        {
            "ollama": {
                "api_base": "http://localhost:11434/v1",
                "api_key_env_var": "",
                "backend": "generic",
                "models": ["llama3:8b", "qwen2.5-coder:14b"],
                "last_fetched_at": datetime.now(UTC).isoformat(),
            }
        }
    )

    config = VibeConfig.load()
    provider_names = [p.name for p in config.providers]
    aliases = [m.alias for m in config.models]

    assert "ollama" in provider_names
    assert "llama3:8b" in aliases
    assert "qwen2.5-coder:14b" in aliases
    ollama_provider = next(p for p in config.providers if p.name == "ollama")
    assert ollama_provider.discovered is True


def test_load_falls_back_when_active_model_disappears(caplog) -> None:
    # Cache has the model the test config expects to be active, then we clear it.
    _write_cache(
        {
            "ollama": {
                "api_base": "http://localhost:11434/v1",
                "api_key_env_var": "",
                "backend": "generic",
                "models": [],
                "last_fetched_at": datetime.now(UTC).isoformat(),
            }
        }
    )
    # Write a TOML referencing a model that doesn't exist anywhere
    import tomli_w

    from vibe.core.config.harness_files import get_harness_files_manager

    target = get_harness_files_manager().user_config_file
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        tomli_w.dumps({"active_model": "ghost-model-from-stale-cache"}),
        encoding="utf-8",
    )

    config = VibeConfig.load()
    assert config.active_model == DEFAULT_ACTIVE_MODEL


def test_load_without_cache_keeps_defaults(tmp_path: Path) -> None:
    # No cache file — VibeConfig.load() should still work, no Ollama appears
    cache = get_cache_path()
    if cache.exists():
        cache.unlink()
    config = VibeConfig.load()
    assert config.active_model
    # No discovered provider should appear when the cache is missing
    assert not any(p.discovered for p in config.providers)


def test_load_idempotent_does_not_duplicate(tmp_path: Path) -> None:
    _write_cache(
        {
            "ollama": {
                "api_base": "http://localhost:11434/v1",
                "api_key_env_var": "",
                "backend": "generic",
                "models": ["llama3:8b"],
                "last_fetched_at": datetime.now(UTC).isoformat(),
            }
        }
    )

    config1 = VibeConfig.load()
    config2 = VibeConfig.load()
    aliases1 = [m.alias for m in config1.models]
    aliases2 = [m.alias for m in config2.models]
    assert aliases1 == aliases2  # idempotent across loads
    assert aliases1.count("llama3:8b") == 1
