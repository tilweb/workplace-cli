"""Tests for dynamic model discovery (Adacor /v1/models + Ollama probe)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import httpx
import pytest
import respx

from vibe.core.config import ProviderConfig
from vibe.core.llm.model_discovery import (
    CACHE_VERSION,
    DEFAULT_TTL_SEC,
    DiscoveryCache,
    _is_chat_model,
    get_ttl_sec,
    load_cache,
    merge_into_config,
    probe_ollama,
    refresh_provider,
    update_cache_entry,
    write_cache,
)
from vibe.core.types import Backend

# ---------- Filter heuristic ----------


@pytest.mark.parametrize(
    "model_id,expected",
    [
        ("qwen3-a3b-30b-256k", True),
        ("qwen3-a3bthinking-30b-256k", True),
        ("mistral-3-24b-128k", True),
        ("pixtral-12b-32k", True),
        ("llama-3-8b-32k", True),
        ("whisper-v3-large-30s", False),
        ("multilingual-e5-large", False),
        ("text-embedding-3-small", False),
        ("nomic-embed-text", False),
        ("voxtral-mini-tts-latest", False),
    ],
)
def test_chat_filter(model_id: str, expected: bool) -> None:
    assert _is_chat_model(model_id) is expected


# ---------- TTL handling ----------


def test_ttl_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORKPLACE_MODEL_CACHE_TTL_SEC", raising=False)
    assert get_ttl_sec() == DEFAULT_TTL_SEC


def test_ttl_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKPLACE_MODEL_CACHE_TTL_SEC", "120")
    assert get_ttl_sec() == 120


def test_ttl_invalid_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKPLACE_MODEL_CACHE_TTL_SEC", "not-an-int")
    assert get_ttl_sec() == DEFAULT_TTL_SEC


def test_is_fresh_within_ttl() -> None:
    cache = DiscoveryCache()
    update_cache_entry(
        cache,
        ProviderConfig(name="adacor", api_base="https://x", api_key_env_var=""),
        ["foo"],
    )
    assert cache.is_fresh("adacor", ttl_sec=3600) is True


def test_is_fresh_expired() -> None:
    stale = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    cache = DiscoveryCache.model_validate(
        {
            "version": CACHE_VERSION,
            "providers": {
                "adacor": {
                    "api_base": "https://x",
                    "models": ["foo"],
                    "last_fetched_at": stale,
                }
            },
        }
    )
    assert cache.is_fresh("adacor", ttl_sec=3600) is False


def test_is_fresh_unknown_provider() -> None:
    cache = DiscoveryCache()
    assert cache.is_fresh("nope") is False


# ---------- Cache file I/O ----------


def test_load_cache_missing_file(tmp_path: Path) -> None:
    cache = load_cache(tmp_path / "no-such.json")
    assert cache.providers == {}


def test_load_cache_corrupt_json(tmp_path: Path) -> None:
    target = tmp_path / "cache.json"
    target.write_text("{not json", encoding="utf-8")
    cache = load_cache(target)
    assert cache.providers == {}


def test_load_cache_wrong_schema(tmp_path: Path) -> None:
    target = tmp_path / "cache.json"
    target.write_text(json.dumps({"version": 1, "providers": "wrong type"}))
    cache = load_cache(target)
    assert cache.providers == {}


def test_load_cache_version_mismatch(tmp_path: Path) -> None:
    target = tmp_path / "cache.json"
    target.write_text(json.dumps({"version": 999, "providers": {}}))
    cache = load_cache(target)
    assert cache.providers == {}


def test_write_then_load_roundtrip(tmp_path: Path) -> None:
    target = tmp_path / "cache.json"
    cache = DiscoveryCache()
    update_cache_entry(
        cache,
        ProviderConfig(
            name="adacor", api_base="https://x", api_key_env_var="K", backend=Backend.GENERIC
        ),
        ["m1", "m2"],
    )
    write_cache(cache, target)

    loaded = load_cache(target)
    assert "adacor" in loaded.providers
    assert loaded.providers["adacor"].models == ["m1", "m2"]
    assert loaded.providers["adacor"].api_key_env_var == "K"


def test_write_cache_atomic(tmp_path: Path) -> None:
    target = tmp_path / "cache.json"
    write_cache(DiscoveryCache(), target)
    # tmp sibling must not exist after a successful write
    assert not (tmp_path / "cache.json.tmp").exists()
    assert target.exists()


# ---------- refresh_provider (HTTP) ----------


_ADACOR_PAYLOAD = {
    "object": "list",
    "data": [
        {"id": "qwen3-a3b-30b-256k", "object": "model"},
        {"id": "qwen3-a3bthinking-30b-256k", "object": "model"},
        {"id": "whisper-v3-large-30s", "object": "model"},
        {"id": "multilingual-e5-large", "object": "model"},
    ],
}


@pytest.mark.asyncio
@respx.mock
async def test_refresh_provider_filters_non_chat() -> None:
    respx.get("https://api.adacor.ai/chat/privateai/v1/models").mock(
        return_value=httpx.Response(200, json=_ADACOR_PAYLOAD)
    )
    provider = ProviderConfig(
        name="adacor",
        api_base="https://api.adacor.ai/chat/privateai/v1",
        api_key_env_var="",
        backend=Backend.GENERIC,
    )
    models = await refresh_provider(provider)
    assert models == ["qwen3-a3b-30b-256k", "qwen3-a3bthinking-30b-256k"]


@pytest.mark.asyncio
@respx.mock
async def test_refresh_provider_sends_auth_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADACOR_AI_API_KEY", "secret-token")
    route = respx.get("https://api.adacor.ai/chat/privateai/v1/models").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": []})
    )
    provider = ProviderConfig(
        name="adacor",
        api_base="https://api.adacor.ai/chat/privateai/v1",
        api_key_env_var="ADACOR_AI_API_KEY",
        backend=Backend.GENERIC,
    )
    await refresh_provider(provider)
    request = route.calls[0].request
    assert request.headers["Authorization"] == "Bearer secret-token"


@pytest.mark.asyncio
@respx.mock
async def test_refresh_provider_skips_auth_when_no_env_var() -> None:
    route = respx.get("https://api.adacor.ai/chat/privateai/v1/models").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": []})
    )
    provider = ProviderConfig(
        name="adacor",
        api_base="https://api.adacor.ai/chat/privateai/v1",
        api_key_env_var="",
        backend=Backend.GENERIC,
    )
    await refresh_provider(provider)
    assert "Authorization" not in route.calls[0].request.headers


@pytest.mark.asyncio
@respx.mock
async def test_refresh_provider_raises_on_non_openai_payload() -> None:
    respx.get("https://x/models").mock(
        return_value=httpx.Response(200, json={"this": "is wrong"})
    )
    provider = ProviderConfig(
        name="adacor", api_base="https://x", backend=Backend.GENERIC
    )
    with pytest.raises(ValueError, match="non-OpenAI"):
        await refresh_provider(provider)


@pytest.mark.asyncio
@respx.mock
async def test_refresh_provider_raises_on_http_error() -> None:
    respx.get("https://x/models").mock(return_value=httpx.Response(500))
    provider = ProviderConfig(name="adacor", api_base="https://x")
    with pytest.raises(httpx.HTTPStatusError):
        await refresh_provider(provider)


# ---------- probe_ollama ----------


@pytest.mark.asyncio
@respx.mock
async def test_probe_ollama_success() -> None:
    respx.get("http://localhost:11434/v1/models").mock(
        return_value=httpx.Response(
            200, json={"object": "list", "data": [{"id": "llama3"}]}
        )
    )
    provider = await probe_ollama()
    assert provider is not None
    assert provider.name == "ollama"
    assert provider.api_base == "http://localhost:11434/v1"
    assert provider.backend == Backend.GENERIC


@pytest.mark.asyncio
@respx.mock
async def test_probe_ollama_connection_refused() -> None:
    respx.get("http://localhost:11434/v1/models").mock(
        side_effect=httpx.ConnectError("refused")
    )
    assert await probe_ollama() is None


@pytest.mark.asyncio
@respx.mock
async def test_probe_ollama_non_200() -> None:
    respx.get("http://localhost:11434/v1/models").mock(
        return_value=httpx.Response(404)
    )
    assert await probe_ollama() is None


@pytest.mark.asyncio
@respx.mock
async def test_probe_ollama_wrong_service_on_port() -> None:
    # Some random service answering 200 with HTML — must not be treated as Ollama
    respx.get("http://localhost:11434/v1/models").mock(
        return_value=httpx.Response(200, text="<html>")
    )
    assert await probe_ollama() is None


# ---------- merge_into_config ----------


def test_merge_appends_only_new_providers_and_models() -> None:
    from vibe.core.config import ModelConfig

    cache = DiscoveryCache.model_validate(
        {
            "version": CACHE_VERSION,
            "providers": {
                "adacor": {
                    "api_base": "https://api.adacor.ai/chat/privateai/v1",
                    "api_key_env_var": "ADACOR_AI_API_KEY",
                    "backend": "generic",
                    "models": ["existing-alias", "brand-new-model"],
                    "last_fetched_at": datetime.now(UTC).isoformat(),
                },
                "ollama": {
                    "api_base": "http://localhost:11434/v1",
                    "api_key_env_var": "",
                    "backend": "generic",
                    "models": ["llama3", "qwen2.5-coder"],
                    "last_fetched_at": datetime.now(UTC).isoformat(),
                },
            },
        }
    )

    class _FakeConfig:
        def __init__(self) -> None:
            self.providers: list[ProviderConfig] = [
                ProviderConfig(
                    name="adacor",
                    api_base="https://api.adacor.ai/chat/privateai/v1",
                    api_key_env_var="ADACOR_AI_API_KEY",
                    backend=Backend.GENERIC,
                )
            ]
            self.models: list[ModelConfig] = [
                ModelConfig(name="existing", provider="adacor", alias="existing-alias")
            ]

    cfg = _FakeConfig()
    merge_into_config(cfg, cache)  # type: ignore[arg-type]

    provider_names = [p.name for p in cfg.providers]
    assert provider_names == ["adacor", "ollama"]  # Ollama appended, adacor not duplicated
    assert any(p.discovered for p in cfg.providers if p.name == "ollama")

    aliases = [m.alias for m in cfg.models]
    assert "existing-alias" in aliases
    assert "brand-new-model" in aliases
    assert "llama3" in aliases
    assert "qwen2.5-coder" in aliases
    assert aliases.count("existing-alias") == 1  # idempotent
