from __future__ import annotations

import pytest

from tests.conftest import build_test_vibe_config
from tests.stubs.fake_audio_recorder import FakeAudioRecorder
from tests.stubs.fake_transcribe_client import FakeTranscribeClient
from vibe.cli.commands import CommandRegistry
from vibe.cli.voice_manager.voice_manager import VoiceManager
from vibe.cli.voice_manager.voice_manager_port import RecordingStartError


@pytest.fixture(autouse=True)
def _disable_voice_features(monkeypatch: pytest.MonkeyPatch) -> None:
    # Overrides the suite-wide _enable_voice_features fixture to assert the
    # production default (voice/narrator hidden).
    monkeypatch.setattr("vibe.cli.feature_flags.VOICE_FEATURES_ENABLED", False)


def _make_manager() -> VoiceManager:
    config = build_test_vibe_config(voice_mode_enabled=True)
    return VoiceManager(
        config_getter=lambda: config,
        audio_recorder=FakeAudioRecorder(),
        transcribe_client=FakeTranscribeClient(),
    )


def test_is_disabled_even_when_config_enables_voice_mode() -> None:
    assert _make_manager().is_enabled is False


def test_start_recording_raises_when_voice_features_disabled() -> None:
    with pytest.raises(RecordingStartError):
        _make_manager().start_recording()


def test_voice_command_is_hidden() -> None:
    assert "voice" not in CommandRegistry().commands
