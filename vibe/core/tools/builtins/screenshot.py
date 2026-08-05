from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
import re
from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, Field

from vibe.core.tools.base import (
    BaseTool,
    BaseToolConfig,
    BaseToolState,
    InvokeContext,
    ToolError,
    ToolPermission,
)
from vibe.core.tools.ui import ToolCallDisplay, ToolResultDisplay, ToolUIData
from vibe.core.types import ToolStreamEvent
from vibe.core.utils.images import build_image_data_url

if TYPE_CHECKING:
    from vibe.core.types import ToolResultEvent

_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")
_MIN_DIMENSION = 100
_MAX_DIMENSION = 4000


class ScreenshotToolConfig(BaseToolConfig):
    permission: ToolPermission = ToolPermission.ASK
    default_width: int = Field(default=1280, description="Default viewport width (px).")
    default_height: int = Field(
        default=800, description="Default viewport height (px)."
    )
    nav_timeout_ms: int = Field(
        default=30_000, description="Navigation timeout in milliseconds."
    )


class ScreenshotArgs(BaseModel):
    url: str = Field(
        description=(
            "Page to capture: an http(s):// URL, or a path to a local HTML file "
            "(absolute, or relative to the working directory). Local paths are "
            "opened via file://."
        )
    )
    full_page: bool = Field(
        default=False,
        description="Capture the entire scrollable page instead of just the viewport.",
    )
    width: int | None = Field(default=None, description="Viewport width in pixels.")
    height: int | None = Field(default=None, description="Viewport height in pixels.")
    wait_for_selector: str | None = Field(
        default=None, description="Optional CSS selector to wait for before capturing."
    )


class ScreenshotResult(BaseModel):
    url: str
    path: str = Field(description="Absolute path to the saved PNG screenshot.")
    width: int
    height: int
    full_page: bool
    # Data URL is attached to the tool response as an image (vision), not echoed
    # back to the model as text.
    image_url: str | None = Field(default=None, exclude=True)


class Screenshot(
    BaseTool[ScreenshotArgs, ScreenshotResult, ScreenshotToolConfig, BaseToolState],
    ToolUIData[ScreenshotArgs, ScreenshotResult],
):
    description: ClassVar[str] = (
        "Render a web page or local HTML file in a headless browser and capture a "
        "screenshot. The image is attached to the result so a vision-capable model "
        "can see the rendered page — use it to visually verify frontend work or "
        "inspect how a URL looks. Requires the bundled Chromium browser."
    )

    async def run(
        self, args: ScreenshotArgs, ctx: InvokeContext | None = None
    ) -> AsyncGenerator[ToolStreamEvent | ScreenshotResult, None]:
        target = self._resolve_url(args.url)
        width = self._clamp_dimension(args.width or self.config.default_width, "width")
        height = self._clamp_dimension(
            args.height or self.config.default_height, "height"
        )
        out_path = self._output_path(ctx)

        await self._capture(args, target, width, height, out_path)

        yield ScreenshotResult(
            url=target,
            path=str(out_path),
            width=width,
            height=height,
            full_page=args.full_page,
            image_url=build_image_data_url(out_path),
        )

    def _resolve_url(self, url: str) -> str:
        raw = url.strip()
        if not raw:
            raise ToolError("Empty URL provided.")
        if _SCHEME_RE.match(raw):
            return raw
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            raise ToolError(f"Local file does not exist: {url}")
        return path.resolve().as_uri()

    @staticmethod
    def _clamp_dimension(value: int, name: str) -> int:
        if value < _MIN_DIMENSION or value > _MAX_DIMENSION:
            raise ToolError(
                f"{name} must be between {_MIN_DIMENSION} and {_MAX_DIMENSION} px."
            )
        return value

    @staticmethod
    def _output_path(ctx: InvokeContext | None) -> Path:
        base = None
        if ctx is not None:
            base = ctx.scratchpad_dir or ctx.session_dir
        base = base or Path.cwd()
        base.mkdir(parents=True, exist_ok=True)
        # Stable-ish name; a later capture in the same session overwrites it.
        return base / "screenshot.png"

    async def _capture(
        self, args: ScreenshotArgs, target: str, width: int, height: int, out_path: Path
    ) -> None:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # pragma: no cover - dependency ships by default
            raise ToolError(
                "Playwright is not installed. Add the 'playwright' package."
            ) from exc

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                try:
                    page = await browser.new_page(
                        viewport={"width": width, "height": height}
                    )
                    await page.goto(
                        target, timeout=self.config.nav_timeout_ms, wait_until="load"
                    )
                    if args.wait_for_selector:
                        await page.wait_for_selector(
                            args.wait_for_selector, timeout=self.config.nav_timeout_ms
                        )
                    await page.screenshot(path=str(out_path), full_page=args.full_page)
                finally:
                    await browser.close()
        except ToolError:
            raise
        except Exception as exc:
            message = str(exc)
            if "Executable doesn't exist" in message or "playwright install" in message:
                raise ToolError(
                    "Chromium for the screenshot tool is not installed yet. "
                    "Install it once with:\n"
                    "  uv tool run --from workplace-cli playwright install chromium\n"
                    "(or, in a dev checkout: uv run playwright install chromium)."
                ) from exc
            raise ToolError(f"Screenshot failed: {message}") from exc

    @classmethod
    def format_call_display(cls, args: ScreenshotArgs) -> ToolCallDisplay:
        summary = f"Screenshot of {args.url}"
        if args.full_page:
            summary += " (full page)"
        return ToolCallDisplay(summary=summary)

    @classmethod
    def get_result_display(cls, event: ToolResultEvent) -> ToolResultDisplay:
        if not isinstance(event.result, ScreenshotResult):
            return ToolResultDisplay(
                success=False, message=event.error or event.skip_reason or "No result"
            )
        return ToolResultDisplay(
            success=True,
            message=f"Captured {event.result.width}×{event.result.height} → {event.result.path}",
        )

    def get_result_images(self, result: ScreenshotResult) -> list[str] | None:
        return [result.image_url] if result.image_url else None

    @classmethod
    def get_status_text(cls) -> str:
        return "Capturing screenshot"
