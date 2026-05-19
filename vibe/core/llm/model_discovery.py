"""ADACOR: dynamic model discovery (no upstream equivalent).

Discovers chat-capable models from OpenAI-compatible providers (Adacor's
private-AI gateway and a locally running Ollama) at runtime, so users can
pick freshly-deployed models via `/model` without editing config files.

Discovered providers and model entries are *virtual*: they are merged into
`VibeConfig.providers` / `.models` on each `VibeConfig.load()` but never
written to `config.toml`. Only the chosen `active_model` alias is persisted.

Cache file: `$VIBE_HOME/models-cache.json` (default `~/.workplace-cli/`).
TTL default 1 hour, overridable via `WORKPLACE_MODEL_CACHE_TTL_SEC`.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
import os
from pathlib import Path
import re
from typing import TYPE_CHECKING

import httpx
from pydantic import BaseModel, ConfigDict, Field

from vibe.core.paths import MODELS_CACHE_FILE
from vibe.core.types import Backend

if TYPE_CHECKING:
    from vibe.core.config import ModelConfig, ProviderConfig, VibeConfig

logger = logging.getLogger(__name__)


CACHE_VERSION = 1
DEFAULT_TTL_SEC = 3600
OLLAMA_API_BASE = "http://localhost:11434/v1"
OLLAMA_PROBE_TIMEOUT_SEC = 0.5
REFRESH_TIMEOUT_SEC = 5.0

# Adacor's /models lists chat, transcribe, and embedding endpoints together.
# Picker is chat-only — filter the rest. Patterns matched against `id` lowercased.
_NON_CHAT_PATTERNS = re.compile(
    r"^(whisper|.*-e5-|.*-embed|.*embedding|.*-tts)", re.IGNORECASE
)


class CachedProvider(BaseModel):
    model_config = ConfigDict(extra="ignore")
    api_base: str
    api_key_env_var: str = ""
    backend: str = "generic"
    models: list[str] = Field(default_factory=list)
    last_fetched_at: str = ""


class DiscoveryCache(BaseModel):
    model_config = ConfigDict(extra="ignore")
    version: int = CACHE_VERSION
    providers: dict[str, CachedProvider] = Field(default_factory=dict)

    def is_fresh(self, name: str, ttl_sec: int = DEFAULT_TTL_SEC) -> bool:
        entry = self.providers.get(name)
        if entry is None or not entry.last_fetched_at:
            return False
        try:
            fetched = datetime.fromisoformat(entry.last_fetched_at)
        except ValueError:
            return False
        age = (datetime.now(UTC) - fetched).total_seconds()
        return age < ttl_sec


def get_cache_path() -> Path:
    return MODELS_CACHE_FILE.path


def get_ttl_sec() -> int:
    raw = os.getenv("WORKPLACE_MODEL_CACHE_TTL_SEC")
    if not raw:
        return DEFAULT_TTL_SEC
    try:
        return max(0, int(raw))
    except ValueError:
        logger.warning(
            "WORKPLACE_MODEL_CACHE_TTL_SEC=%r is not an integer — using default", raw
        )
        return DEFAULT_TTL_SEC


def load_cache(path: Path | None = None) -> DiscoveryCache:
    """Read the cache file, returning an empty cache if missing or corrupt."""
    target = path or get_cache_path()
    if not target.exists():
        return DiscoveryCache()
    try:
        raw = json.loads(target.read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("models-cache.json unreadable (%s) — ignoring", exc)
        return DiscoveryCache()
    try:
        cache = DiscoveryCache.model_validate(raw)
    except Exception as exc:
        logger.warning("models-cache.json schema mismatch (%s) — ignoring", exc)
        return DiscoveryCache()
    if cache.version != CACHE_VERSION:
        return DiscoveryCache()
    return cache


def write_cache(cache: DiscoveryCache, path: Path | None = None) -> None:
    """Persist the cache atomically (tmp + rename)."""
    target = path or get_cache_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(cache.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(target)


def _is_chat_model(model_id: str) -> bool:
    return not _NON_CHAT_PATTERNS.match(model_id)


def _is_openai_models_payload(data: object) -> bool:
    return (
        isinstance(data, dict)
        and data.get("object") == "list"
        and isinstance(data.get("data"), list)
    )


def _extract_model_ids(payload: dict[str, object]) -> list[str]:
    out: list[str] = []
    for item in payload.get("data", []):  # type: ignore[union-attr]
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            out.append(item["id"])
    return out


async def refresh_provider(
    provider: ProviderConfig, *, timeout_sec: float = REFRESH_TIMEOUT_SEC
) -> list[str]:
    """Fetch the model list from `<api_base>/models`.

    Returns chat-capable model IDs. Raises httpx exceptions on network
    failure — callers should handle per-provider isolation.
    """
    url = f"{provider.api_base.rstrip('/')}/models"
    headers: dict[str, str] = {"Accept": "application/json"}
    if provider.api_key_env_var:
        key = os.getenv(provider.api_key_env_var)
        if key:
            headers["Authorization"] = f"Bearer {key}"
    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        payload = response.json()
    if not _is_openai_models_payload(payload):
        raise ValueError(
            f"Provider {provider.name!r} returned non-OpenAI models payload"
        )
    return [mid for mid in _extract_model_ids(payload) if _is_chat_model(mid)]


async def probe_ollama(
    *, timeout_sec: float = OLLAMA_PROBE_TIMEOUT_SEC
) -> ProviderConfig | None:
    """Quick check whether a local Ollama server is reachable.

    Returns a `ProviderConfig` for Ollama if the port responds with an
    OpenAI-shaped payload, else `None`. Errors (timeout, ConnectionRefused,
    wrong service on the port) all map to `None`.
    """
    from vibe.core.config import ProviderConfig

    url = f"{OLLAMA_API_BASE}/models"
    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            response = await client.get(url)
        if response.status_code != httpx.codes.OK:
            return None
        if not _is_openai_models_payload(response.json()):
            return None
    except (httpx.HTTPError, ValueError, json.JSONDecodeError):
        return None
    return ProviderConfig(
        name="ollama",
        api_base=OLLAMA_API_BASE,
        api_key_env_var="",
        backend=Backend.GENERIC,
        discovered=True,
    )


def update_cache_entry(
    cache: DiscoveryCache, provider: ProviderConfig, models: list[str]
) -> None:
    cache.providers[provider.name] = CachedProvider(
        api_base=provider.api_base,
        api_key_env_var=provider.api_key_env_var,
        backend=str(provider.backend),
        models=models,
        last_fetched_at=datetime.now(UTC).isoformat(),
    )


def _build_provider_from_cache(name: str, entry: CachedProvider) -> ProviderConfig:
    from vibe.core.config import ProviderConfig

    try:
        backend = Backend(entry.backend)
    except ValueError:
        backend = Backend.GENERIC
    return ProviderConfig(
        name=name,
        api_base=entry.api_base,
        api_key_env_var=entry.api_key_env_var,
        backend=backend,
        discovered=True,
    )


def _build_model_from_cache(model_id: str, provider_name: str) -> ModelConfig:
    from vibe.core.config import ModelConfig

    return ModelConfig(name=model_id, provider=provider_name, alias=model_id)


def merge_into_config(config: VibeConfig, cache: DiscoveryCache) -> None:
    """Inject cached providers and models into a live `VibeConfig` instance.

    Idempotent: hard-coded entries win on alias/provider-name conflicts.
    Mutates `config.providers` and `config.models` in place.
    """
    existing_provider_names = {p.name for p in config.providers}
    for name, entry in cache.providers.items():
        if name not in existing_provider_names:
            config.providers.append(_build_provider_from_cache(name, entry))

    existing_aliases = {m.alias for m in config.models}
    for name, entry in cache.providers.items():
        for model_id in entry.models:
            if model_id in existing_aliases:
                continue
            config.models.append(_build_model_from_cache(model_id, name))
            existing_aliases.add(model_id)
