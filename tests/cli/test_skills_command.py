"""Tests for the /skills command."""

from __future__ import annotations

from collections.abc import Iterator
from types import MappingProxyType
from unittest.mock import patch

import pytest

from tests.conftest import build_test_vibe_app, build_test_vibe_config
from vibe.cli.textual_ui.widgets.messages import UserCommandMessage
from vibe.core.config._settings import ModelConfig
from vibe.core.skills.models import SkillInfo


def _make_config():
    models = [ModelConfig(name="m", provider="mistral", alias="m")]
    return build_test_vibe_config(models=models, active_model="m")


def _make_skill(
    name: str, description: str, user_invocable: bool = True
) -> SkillInfo:
    return SkillInfo(
        name=name,
        description=description,
        user_invocable=user_invocable,
        prompt=f"# {name}\n\nbody",
    )


@pytest.fixture(autouse=True)
def _empty_message_buffer() -> Iterator[None]:
    yield


@pytest.mark.asyncio
async def test_skills_command_lists_invocable_and_auto_groups() -> None:
    app = build_test_vibe_app(config=_make_config())

    available = {
        "adacor-review": _make_skill("adacor-review", "Review code", True),
        "deep-research": _make_skill("deep-research", "Research helper", True),
        "vibe": _make_skill("vibe", "Self-awareness", user_invocable=False),
    }

    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        with patch.object(
            app.agent_loop.skill_manager,
            "available_skills",
            MappingProxyType(available),
        ):
            await app._show_skills()
            await pilot.pause(0.2)

        rendered = "\n".join(
            msg._content for msg in app.query(UserCommandMessage)
        )

    assert "## Skills" in rendered
    assert "/adacor-review" in rendered
    assert "Review code" in rendered
    assert "/deep-research" in rendered
    # Non-invocable skill listed under the auto section by its bare name, not as /name
    assert "Auto-loaded by the agent" in rendered
    assert "vibe" in rendered
    assert "/vibe" not in rendered


@pytest.mark.asyncio
async def test_skills_command_when_empty_shows_setup_hint() -> None:
    app = build_test_vibe_app(config=_make_config())
    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        with patch.object(
            app.agent_loop.skill_manager,
            "available_skills",
            MappingProxyType({}),
        ):
            await app._show_skills()
            await pilot.pause(0.2)

        rendered = "\n".join(
            msg._content for msg in app.query(UserCommandMessage)
        )

    assert "No skills are currently loaded" in rendered
    assert "~/.workplace-cli/skills/" in rendered
