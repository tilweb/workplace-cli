from __future__ import annotations

from pathlib import Path

import pytest

from tests.mock.utils import collect_result
from vibe.core.tools.base import BaseToolState, InvokeContext, ToolError
from vibe.core.tools.builtins.screenshot import (
    Screenshot,
    ScreenshotArgs,
    ScreenshotToolConfig,
)


def _chromium_ready() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            executable = pw.chromium.executable_path
        return bool(executable) and Path(executable).exists()
    except Exception:
        return False


@pytest.fixture
def screenshot_tool(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = ScreenshotToolConfig()
    return Screenshot(config_getter=lambda: config, state=BaseToolState())


def test_resolve_local_path_becomes_file_uri(screenshot_tool, tmp_path):
    page = tmp_path / "page.html"
    page.write_text("<html></html>")
    resolved = screenshot_tool._resolve_url("page.html")
    assert resolved.startswith("file://")
    assert resolved.endswith("page.html")


def test_resolve_http_url_passthrough(screenshot_tool):
    assert screenshot_tool._resolve_url("https://example.com") == "https://example.com"


def test_resolve_missing_file_raises(screenshot_tool):
    with pytest.raises(ToolError) as err:
        screenshot_tool._resolve_url("/nope/missing.html")
    assert "does not exist" in str(err.value)


def test_resolve_empty_url_raises(screenshot_tool):
    with pytest.raises(ToolError):
        screenshot_tool._resolve_url("   ")


@pytest.mark.asyncio
async def test_dimension_below_minimum_raises(screenshot_tool, tmp_path):
    page = tmp_path / "page.html"
    page.write_text("<html></html>")
    with pytest.raises(ToolError) as err:
        await collect_result(
            screenshot_tool.run(ScreenshotArgs(url="page.html", width=50))
        )
    assert "between" in str(err.value)


@pytest.mark.asyncio
async def test_dimension_above_maximum_raises(screenshot_tool, tmp_path):
    page = tmp_path / "page.html"
    page.write_text("<html></html>")
    with pytest.raises(ToolError):
        await collect_result(
            screenshot_tool.run(ScreenshotArgs(url="page.html", height=9000))
        )


@pytest.mark.skipif(
    not _chromium_ready(), reason="Playwright Chromium browser not installed"
)
@pytest.mark.asyncio
async def test_renders_local_html_and_attaches_image(screenshot_tool, tmp_path):
    page = tmp_path / "page.html"
    page.write_text(
        "<html><body style='background:#0a0'>Workplace</body></html>"
    )
    ctx = InvokeContext(tool_call_id="t1", scratchpad_dir=tmp_path)

    result = await collect_result(
        screenshot_tool.run(ScreenshotArgs(url="page.html", width=400, height=300), ctx)
    )

    assert Path(result.path).exists()
    assert Path(result.path).stat().st_size > 0
    images = screenshot_tool.get_result_images(result)
    assert images and images[0].startswith("data:image/png;base64,")
    # image_url must not leak into the text result model dump
    assert "image_url" not in result.model_dump()
