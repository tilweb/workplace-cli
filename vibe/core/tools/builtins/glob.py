from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
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
from vibe.core.tools.permissions import PermissionContext
from vibe.core.tools.ui import ToolCallDisplay, ToolResultDisplay, ToolUIData
from vibe.core.tools.utils import resolve_file_tool_permission
from vibe.core.types import ToolStreamEvent

if TYPE_CHECKING:
    from vibe.core.types import ToolResultEvent


class GlobToolConfig(BaseToolConfig):
    permission: ToolPermission = ToolPermission.ALWAYS
    sensitive_patterns: list[str] = Field(
        default=["**/.env", "**/.env.*"],
        description="File patterns that trigger ASK even when permission is ALWAYS.",
    )

    default_max_results: int = Field(
        default=100, description="Default maximum number of paths to return."
    )
    exclude_dirs: list[str] = Field(
        default=[
            ".git",
            ".venv",
            "venv",
            "env",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".tox",
            ".nox",
            "dist",
            "build",
            ".idea",
            ".vscode",
        ],
        description="Directory names skipped anywhere in a matched path.",
    )


class GlobArgs(BaseModel):
    pattern: str = Field(
        description=(
            "Glob pattern to match file names against, e.g. '**/*.py', "
            "'src/**/*.ts', or 'README*'. Use '**' to recurse into subdirectories."
        )
    )
    path: str = Field(
        default=".",
        description="Base directory to search from. Defaults to the current directory.",
    )
    max_results: int | None = Field(
        default=None, description="Override the default maximum number of results."
    )


class GlobResult(BaseModel):
    paths: str = Field(description="Newline-separated absolute file paths.")
    match_count: int
    was_truncated: bool = Field(
        description="True if the result was cut short by max_results."
    )


class Glob(
    BaseTool[GlobArgs, GlobResult, GlobToolConfig, BaseToolState],
    ToolUIData[GlobArgs, GlobResult],
):
    description: ClassVar[str] = (
        "Find files by name using a glob pattern (e.g. '**/*.py'). "
        "Returns matching file paths sorted by modification time, most recent "
        "first. Fast for locating files when you know part of the name; use grep "
        "to search file contents instead."
    )

    def resolve_permission(self, args: GlobArgs) -> PermissionContext | None:
        return resolve_file_tool_permission(
            args.path,
            tool_name=self.get_name(),
            allowlist=self.config.allowlist,
            denylist=self.config.denylist,
            config_permission=self.config.permission,
            sensitive_patterns=self.config.sensitive_patterns,
        )

    async def run(
        self, args: GlobArgs, ctx: InvokeContext | None = None
    ) -> AsyncGenerator[ToolStreamEvent | GlobResult, None]:
        base = self._resolve_base(args.path)
        max_results = args.max_results or self.config.default_max_results

        matches = self._collect_matches(base, args.pattern)
        matches.sort(key=self._mtime, reverse=True)

        was_truncated = len(matches) > max_results
        truncated = matches[:max_results]

        yield GlobResult(
            paths="\n".join(str(p) for p in truncated),
            match_count=len(truncated),
            was_truncated=was_truncated,
        )

    def _resolve_base(self, path: str) -> Path:
        base = Path(path).expanduser()
        if not base.is_absolute():
            base = Path.cwd() / base
        if not base.exists():
            raise ToolError(f"Path does not exist: {path}")
        if not base.is_dir():
            raise ToolError(f"Path is not a directory: {path}")
        return base

    def _collect_matches(self, base: Path, pattern: str) -> list[Path]:
        if not pattern.strip():
            raise ToolError("Empty glob pattern provided.")
        excluded = set(self.config.exclude_dirs)
        matches: list[Path] = []
        try:
            for candidate in base.glob(pattern):
                if not candidate.is_file():
                    continue
                if excluded.intersection(candidate.parts):
                    continue
                matches.append(candidate.resolve())
        except (ValueError, OSError) as exc:
            raise ToolError(f"Invalid glob pattern '{pattern}': {exc}") from exc
        return matches

    @staticmethod
    def _mtime(path: Path) -> float:
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0

    @classmethod
    def format_call_display(cls, args: GlobArgs) -> ToolCallDisplay:
        summary = f"Finding '{args.pattern}'"
        if args.path != ".":
            summary += f" in {args.path}"
        return ToolCallDisplay(summary=summary)

    @classmethod
    def get_result_display(cls, event: ToolResultEvent) -> ToolResultDisplay:
        if not isinstance(event.result, GlobResult):
            return ToolResultDisplay(
                success=False, message=event.error or event.skip_reason or "No result"
            )

        message = f"Found {event.result.match_count} files"
        warnings = []
        if event.result.was_truncated:
            message += " (truncated)"
            warnings.append("Output was truncated due to the result limit")

        return ToolResultDisplay(success=True, message=message, warnings=warnings)

    @classmethod
    def get_status_text(cls) -> str:
        return "Finding files"
