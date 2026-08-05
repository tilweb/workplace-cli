from __future__ import annotations

import pytest

from tests.mock.utils import collect_result
from vibe.core.memory import MemoryManager
from vibe.core.tools.base import BaseToolState, ToolError
from vibe.core.tools.builtins.remember import (
    MemoryAction,
    Remember,
    RememberArgs,
    RememberToolConfig,
)


@pytest.fixture
def remember_tool(tmp_path, monkeypatch):
    # Point the store at an isolated home so the real ~/.workplace-cli is untouched.
    monkeypatch.setenv("WORKPLACE_HOME", str(tmp_path))
    config = RememberToolConfig()
    return Remember(config_getter=lambda: config, state=BaseToolState())


@pytest.mark.asyncio
async def test_write_stores_memory_and_index(remember_tool):
    result = await collect_result(
        remember_tool.run(
            RememberArgs(
                name="deploy-command",
                content="Deploy via make ship.",
                description="How to deploy",
            )
        )
    )

    assert result.action == MemoryAction.WRITE
    assert result.stored is True
    assert "deploy-command" in result.message

    index = MemoryManager().load_index() or ""
    assert "[deploy-command](deploy-command.md)" in index
    assert "How to deploy" in index


@pytest.mark.asyncio
async def test_write_requires_content(remember_tool):
    with pytest.raises(ToolError) as err:
        await collect_result(
            remember_tool.run(RememberArgs(name="x", description="desc"))
        )
    assert "content" in str(err.value)


@pytest.mark.asyncio
async def test_write_requires_description(remember_tool):
    with pytest.raises(ToolError) as err:
        await collect_result(
            remember_tool.run(RememberArgs(name="x", content="body"))
        )
    assert "description" in str(err.value)


@pytest.mark.asyncio
async def test_invalid_name_raises(remember_tool):
    with pytest.raises(ToolError):
        await collect_result(
            remember_tool.run(
                RememberArgs(name="Bad Name", content="body", description="desc")
            )
        )


@pytest.mark.asyncio
async def test_delete_removes_memory(remember_tool):
    await collect_result(
        remember_tool.run(
            RememberArgs(name="temp", content="body", description="desc")
        )
    )

    result = await collect_result(
        remember_tool.run(RememberArgs(action=MemoryAction.DELETE, name="temp"))
    )

    assert result.action == MemoryAction.DELETE
    assert result.stored is True
    assert MemoryManager().load_index() is None


@pytest.mark.asyncio
async def test_delete_missing_reports_not_stored(remember_tool):
    result = await collect_result(
        remember_tool.run(RememberArgs(action=MemoryAction.DELETE, name="ghost"))
    )
    assert result.stored is False
    assert "No memory" in result.message
