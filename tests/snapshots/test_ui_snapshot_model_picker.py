from __future__ import annotations

from unittest.mock import patch

import pytest
from textual.pilot import Pilot

from tests.conftest import build_test_vibe_config
from tests.snapshots.base_snapshot_test_app import BaseSnapshotTestApp
from tests.snapshots.snap_compare import SnapCompare
from vibe.core.config._settings import ModelConfig


async def _deterministic_refresh(self) -> None:
    """Finalise the picker from the configured models only.

    The real ``_refresh_models_async`` probes Ollama, hits the Adacor
    ``/models`` endpoint, reads/writes the on-disk discovery cache and reloads
    the config from disk — all of which make the rendered model list depend on
    the host environment (and mutate the real cache). For a deterministic
    snapshot we skip discovery entirely and render just the injected test
    config, mirroring only the picker-finalisation tail of the production path.
    """
    from vibe.cli.textual_ui.app import BottomApp
    from vibe.cli.textual_ui.widgets.model_picker import ModelPickerApp

    if self._current_bottom_app != BottomApp.ModelPicker:
        return
    try:
        picker = self.query_one(ModelPickerApp)
    except Exception:
        return
    picker.update_models(self._build_models_by_provider(), loading=False)


@pytest.fixture(autouse=True)
def _no_live_model_discovery(monkeypatch):
    """Keep the model picker independent of host models / network / cache."""
    monkeypatch.setattr(
        "vibe.cli.textual_ui.app.VibeApp._refresh_models_async",
        _deterministic_refresh,
    )


def _model_picker_config():
    models = [
        ModelConfig(
            name="mistral-large-latest", provider="mistral", alias="mistral-large"
        ),
        ModelConfig(name="devstral-latest", provider="mistral", alias="devstral"),
        ModelConfig(name="codestral-latest", provider="mistral", alias="codestral"),
        ModelConfig(
            name="mistral-small-latest", provider="mistral", alias="mistral-small"
        ),
        ModelConfig(name="devstral", provider="llamacpp", alias="local"),
    ]
    return build_test_vibe_config(
        models=models,
        active_model="devstral",
        disable_welcome_banner_animation=True,
        displayed_workdir="/test/workdir",
    )


class ModelPickerTestApp(BaseSnapshotTestApp):
    def __init__(self):
        super().__init__(config=_model_picker_config())

    async def on_mount(self) -> None:
        await super().on_mount()
        await self._switch_to_model_picker_app()


def test_snapshot_model_picker_initial(snap_compare: SnapCompare) -> None:
    async def run_before(pilot: Pilot) -> None:
        await pilot.pause(0.2)

    assert snap_compare(
        "test_ui_snapshot_model_picker.py:ModelPickerTestApp",
        terminal_size=(100, 36),
        run_before=run_before,
    )


def test_snapshot_model_picker_navigate_down(snap_compare: SnapCompare) -> None:
    async def run_before(pilot: Pilot) -> None:
        await pilot.pause(0.2)
        await pilot.press("down")
        await pilot.pause(0.1)

    assert snap_compare(
        "test_ui_snapshot_model_picker.py:ModelPickerTestApp",
        terminal_size=(100, 36),
        run_before=run_before,
    )


def test_snapshot_model_picker_select_different_model(
    snap_compare: SnapCompare,
) -> None:
    """Select the second model and verify the picker closes back to input."""

    async def run_before(pilot: Pilot) -> None:
        await pilot.pause(0.2)
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.pause(0.2)

    with patch("vibe.cli.textual_ui.app.VibeConfig.save_updates"):
        assert snap_compare(
            "test_ui_snapshot_model_picker.py:ModelPickerTestApp",
            terminal_size=(100, 36),
            run_before=run_before,
        )


def test_snapshot_model_picker_escape_cancels(snap_compare: SnapCompare) -> None:
    async def run_before(pilot: Pilot) -> None:
        await pilot.pause(0.2)
        await pilot.press("escape")
        await pilot.pause(0.2)

    assert snap_compare(
        "test_ui_snapshot_model_picker.py:ModelPickerTestApp",
        terminal_size=(100, 36),
        run_before=run_before,
    )
