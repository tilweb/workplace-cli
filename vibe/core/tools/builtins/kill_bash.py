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
    ToolPermission,
)
from vibe.core.tools.ui import ToolCallDisplay, ToolResultDisplay, ToolUIData
from vibe.core.types import ToolStreamEvent

if TYPE_CHECKING:
    from vibe.core.types import ToolResultEvent


class KillBashToolConfig(BaseToolConfig):
    permission: ToolPermission = ToolPermission.ALWAYS


class KillBashArgs(BaseModel):
    shell_id: str = Field(
        description="Identifier of the background shell (e.g. 'bash-1') to stop."
    )


class KillBashResult(BaseModel):
    shell_id: str
    killed: bool = Field(
        description="True if the shell existed and was signalled to stop."
    )
    message: str


class KillBash(
    BaseTool[KillBashArgs, KillBashResult, KillBashToolConfig, BaseToolState],
    ToolUIData[KillBashArgs, KillBashResult],
):
    description: ClassVar[str] = (
        "Terminate a background shell started with bash(run_in_background=True), "
        "killing its whole process group."
    )

    async def run(
        self, args: KillBashArgs, ctx: InvokeContext | None = None
    ) -> AsyncGenerator[ToolStreamEvent | KillBashResult, None]:
        manager = get_background_manager()
        killed = await manager.kill(args.shell_id)
        yield KillBashResult(
            shell_id=args.shell_id,
            killed=killed,
            message=(
                f"Stopped {args.shell_id}."
                if killed
                else f"No background shell {args.shell_id!r} to stop."
            ),
        )

    @classmethod
    def format_call_display(cls, args: KillBashArgs) -> ToolCallDisplay:
        return ToolCallDisplay(summary=f"Stopping {args.shell_id}")

    @classmethod
    def get_result_display(cls, event: ToolResultEvent) -> ToolResultDisplay:
        if not isinstance(event.result, KillBashResult):
            return ToolResultDisplay(
                success=False, message=event.error or event.skip_reason or "No result"
            )
        return ToolResultDisplay(success=True, message=event.result.message)

    @classmethod
    def get_status_text(cls) -> str:
        return "Stopping background shell"
