from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, Field

from vibe.core.tools.background import get_background_manager
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

if TYPE_CHECKING:
    from vibe.core.types import ToolResultEvent


class BashOutputToolConfig(BaseToolConfig):
    permission: ToolPermission = ToolPermission.ALWAYS
    max_output_bytes: int = Field(
        default=16_000,
        description="Maximum bytes of new stdout/stderr to return per read.",
    )


class BashOutputArgs(BaseModel):
    shell_id: str = Field(
        description="Identifier of the background shell (e.g. 'bash-1') to read."
    )


class BashOutputResult(BaseModel):
    shell_id: str
    stdout: str = Field(description="New stdout since the previous read.")
    stderr: str = Field(description="New stderr since the previous read.")
    running: bool
    returncode: int | None = None


class BashOutput(
    BaseTool[BashOutputArgs, BashOutputResult, BashOutputToolConfig, BaseToolState],
    ToolUIData[BashOutputArgs, BashOutputResult],
):
    description: ClassVar[str] = (
        "Read new output from a background shell started with "
        "bash(run_in_background=True). Returns stdout/stderr produced since the "
        "last read, plus whether the process is still running and its exit code."
    )

    async def run(
        self, args: BashOutputArgs, ctx: InvokeContext | None = None
    ) -> AsyncGenerator[ToolStreamEvent | BashOutputResult, None]:
        manager = get_background_manager()
        bp = manager.get(args.shell_id)
        if bp is None:
            known = ", ".join(p.shell_id for p in manager.list()) or "none"
            raise ToolError(
                f"No background shell {args.shell_id!r}. Known shells: {known}."
            )

        stdout, stderr = manager.read_new(bp)
        cap = self.config.max_output_bytes
        yield BashOutputResult(
            shell_id=bp.shell_id,
            stdout=stdout[-cap:],
            stderr=stderr[-cap:],
            running=bp.running,
            returncode=bp.returncode,
        )

    @classmethod
    def format_call_display(cls, args: BashOutputArgs) -> ToolCallDisplay:
        return ToolCallDisplay(summary=f"Reading output of {args.shell_id}")

    @classmethod
    def get_result_display(cls, event: ToolResultEvent) -> ToolResultDisplay:
        if not isinstance(event.result, BashOutputResult):
            return ToolResultDisplay(
                success=False, message=event.error or event.skip_reason or "No result"
            )
        state = (
            "running" if event.result.running else f"exited ({event.result.returncode})"
        )
        return ToolResultDisplay(
            success=True, message=f"{event.result.shell_id}: {state}"
        )

    @classmethod
    def get_status_text(cls) -> str:
        return "Reading background output"
