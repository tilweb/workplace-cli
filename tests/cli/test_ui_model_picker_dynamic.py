"""Pilot tests for dynamic model discovery in the /model picker."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import build_test_vibe_app, build_test_vibe_config
from vibe.cli.textual_ui.app import BottomApp
from vibe.cli.textual_ui.widgets.model_picker import ModelPickerApp
from vibe.core.config import ModelConfig, ProviderConfig
from vibe.core.llm.model_discovery import CACHE_VERSION, get_cache_path
from vibe.core.types import Backend


def _make_config():
    providers = [
        ProviderConfig(
            name="mistral",
            api_base="https://api.mistral.ai/v1",
            api_key_env_var="MISTRAL_API_KEY",
            backend=Backend.MISTRAL,
        )
    ]
    models = [
        ModelConfig(name="mistral-vibe-cli-latest", provider="mistral", alias="mistral")
    ]
    return build_test_vibe_config(
        providers=providers, models=models, active_model="mistral"
    )


@pytest.mark.asyncio
async def test_picker_opens_in_loading_state() -> None:
    with patch(
        "vibe.cli.textual_ui.app.VibeApp._refresh_models_async",
        new=AsyncMock(return_value=None),
    ):
        app = build_test_vibe_app(config=_make_config())
        async with app.run_test() as pilot:
            await pilot.pause(0.1)
            await app._show_model()
            await pilot.pause(0.2)

            picker = app.query_one(ModelPickerApp)
            assert picker._loading is True
            # Already-known model present even before discovery resolves
            aliases = [
                e.alias
                for entries in picker._models_by_provider.values()
                for e in entries
            ]
            assert "mistral" in aliases


@pytest.mark.asyncio
async def test_picker_groups_models_by_provider() -> None:
    """Cached Ollama entries must show up under their own provider section."""
    target = get_cache_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "version": CACHE_VERSION,
                "providers": {
                    "ollama": {
                        "api_base": "http://localhost:11434/v1",
                        "api_key_env_var": "",
                        "backend": "generic",
                        "models": ["llama3:8b"],
                        "last_fetched_at": datetime.now(UTC).isoformat(),
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    from vibe.core.config import VibeConfig

    config = VibeConfig.load()

    with patch(
        "vibe.cli.textual_ui.app.VibeApp._refresh_models_async",
        new=AsyncMock(return_value=None),
    ):
        app = build_test_vibe_app(config=config)
        async with app.run_test() as pilot:
            await pilot.pause(0.1)
            await app._show_model()
            await pilot.pause(0.2)

            picker = app.query_one(ModelPickerApp)
            assert "ollama" in picker._models_by_provider
            ollama_entries = picker._models_by_provider["ollama"]
            assert any(e.alias == "llama3:8b" for e in ollama_entries)
            assert all(e.is_discovered for e in ollama_entries)


@pytest.mark.asyncio
async def test_picker_select_discovered_model_persists_active_alias() -> None:
    target = get_cache_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "version": CACHE_VERSION,
                "providers": {
                    "adacor": {
                        "api_base": "https://api.adacor.ai/chat/privateai/v1",
                        "api_key_env_var": "ADACOR_AI_API_KEY",
                        "backend": "generic",
                        "models": ["qwen3-a3bthinking-30b-256k"],
                        "last_fetched_at": datetime.now(UTC).isoformat(),
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    from vibe.core.config import VibeConfig

    config = VibeConfig.load()

    with patch(
        "vibe.cli.textual_ui.app.VibeApp._refresh_models_async",
        new=AsyncMock(return_value=None),
    ):
        app = build_test_vibe_app(config=config)
        async with app.run_test() as pilot:
            await pilot.pause(0.1)
            await app._show_model()
            await pilot.pause(0.2)

            # Navigate to the discovered model and select it.
            await pilot.press("down")
            with patch(
                "vibe.cli.textual_ui.app.VibeConfig.save_updates"
            ) as mock_save:
                await pilot.press("enter")
                await pilot.pause(0.2)

            assert mock_save.call_count == 1
            saved = mock_save.call_args[0][0]
            assert saved["active_model"] == "qwen3-a3bthinking-30b-256k"
            assert app._current_bottom_app == BottomApp.Input


@pytest.mark.asyncio
async def test_picker_disabled_header_cannot_be_selected() -> None:
    with patch(
        "vibe.cli.textual_ui.app.VibeApp._refresh_models_async",
        new=AsyncMock(return_value=None),
    ):
        app = build_test_vibe_app(config=_make_config())
        async with app.run_test() as pilot:
            await pilot.pause(0.1)
            await app._show_model()
            await pilot.pause(0.2)

            picker = app.query_one(ModelPickerApp)
            from textual.widgets import OptionList

            option_list = picker.query_one(OptionList)
            # The first option must be the provider header and disabled.
            first = option_list._options[0]
            assert first.disabled is True
            assert first.id and first.id.startswith("__header__")
