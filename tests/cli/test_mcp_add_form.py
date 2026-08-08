from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from vibe.cli.mcp_cli import configured_servers
from vibe.cli.textual_ui.widgets.mcp_add_app import McpAddApp


class _Host(App):
    def __init__(self) -> None:
        super().__init__()
        self.closed: McpAddApp.McpAddClosed | None = None

    def compose(self) -> ComposeResult:
        yield McpAddApp()

    def on_mcp_add_app_mcp_add_closed(self, message: McpAddApp.McpAddClosed) -> None:
        self.closed = message


@pytest.mark.asyncio
async def test_form_saves_http_server():
    app = _Host()
    async with app.run_test() as pilot:
        form = app.query_one(McpAddApp)
        form.inputs["name"].value = "youtrack"
        form.inputs["url"].value = "https://adacor.youtrack.cloud/mcp"
        form.inputs["api_key_env"].value = "YOUTRACK_TOKEN"
        form._save_and_close()
        await pilot.pause()

    assert app.closed is not None
    assert app.closed.saved is True
    assert app.closed.name == "youtrack"

    servers = {s["name"]: s for s in configured_servers()}
    assert "youtrack" in servers
    assert servers["youtrack"]["url"] == "https://adacor.youtrack.cloud/mcp"
    assert servers["youtrack"]["api_key_env"] == "YOUTRACK_TOKEN"


@pytest.mark.asyncio
async def test_form_missing_url_reports_error():
    app = _Host()
    async with app.run_test() as pilot:
        form = app.query_one(McpAddApp)
        form.inputs["name"].value = "broken"
        # url left empty
        form._save_and_close()
        await pilot.pause()

    assert app.closed is not None
    assert app.closed.saved is False
    assert app.closed.error
    assert configured_servers() == []


@pytest.mark.asyncio
async def test_cancel_saves_nothing():
    app = _Host()
    async with app.run_test() as pilot:
        form = app.query_one(McpAddApp)
        form.inputs["name"].value = "youtrack"
        form.inputs["url"].value = "https://x/mcp"
        form.action_close()
        await pilot.pause()

    assert app.closed is not None
    assert app.closed.saved is False
    assert configured_servers() == []
