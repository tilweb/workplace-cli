from __future__ import annotations

from collections.abc import AsyncGenerator
from enum import StrEnum, auto
from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, Field

from vibe.core.memory import MemoryManager, MemoryStoreError
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


class MemoryAction(StrEnum):
    WRITE = auto()
    DELETE = auto()


class RememberToolConfig(BaseToolConfig):
    permission: ToolPermission = ToolPermission.ALWAYS


class RememberArgs(BaseModel):
    action: MemoryAction = Field(
        default=MemoryAction.WRITE,
        description="'write' to store or update a memory, 'delete' to remove one.",
    )
    name: str = Field(
        description=(
            "Stable kebab-case identifier for the memory, e.g. 'deploy-command' "
            "or 'user-prefers-german'. Reusing a name overwrites that memory."
        )
    )
    content: str | None = Field(
        default=None,
        description="The fact to remember (required for 'write'). Keep it to one "
        "durable fact; write in full sentences.",
    )
    description: str | None = Field(
        default=None,
        description="One-line summary used in the memory index to decide relevance "
        "later (required for 'write').",
    )


class RememberResult(BaseModel):
    action: MemoryAction
    name: str
    stored: bool = Field(description="True if the memory now exists / was removed.")
    message: str


class Remember(
    BaseTool[RememberArgs, RememberResult, RememberToolConfig, BaseToolState],
    ToolUIData[RememberArgs, RememberResult],
):
    description: ClassVar[str] = (
        "Save a durable fact to cross-session memory so it survives after this "
        "conversation ends. Use for stable user preferences, project conventions, "
        "or environment facts the user asks you to remember — not for transient "
        "task state. Stored memories are surfaced automatically in future sessions."
    )

    def _manager(self) -> MemoryManager:
        return MemoryManager()

    async def run(
        self, args: RememberArgs, ctx: InvokeContext | None = None
    ) -> AsyncGenerator[ToolStreamEvent | RememberResult, None]:
        manager = self._manager()
        try:
            match args.action:
                case MemoryAction.WRITE:
                    yield self._write(manager, args)
                case MemoryAction.DELETE:
                    yield self._delete(manager, args)
        except MemoryStoreError as exc:
            raise ToolError(str(exc)) from exc

    def _write(self, manager: MemoryManager, args: RememberArgs) -> RememberResult:
        if not (args.content and args.content.strip()):
            raise ToolError("'content' is required when action is 'write'.")
        if not (args.description and args.description.strip()):
            raise ToolError("'description' is required when action is 'write'.")
        path = manager.write_memory(args.name, args.content, args.description)
        return RememberResult(
            action=MemoryAction.WRITE,
            name=args.name,
            stored=True,
            message=f"Remembered '{args.name}' ({path}).",
        )

    def _delete(self, manager: MemoryManager, args: RememberArgs) -> RememberResult:
        removed = manager.delete_memory(args.name)
        return RememberResult(
            action=MemoryAction.DELETE,
            name=args.name,
            stored=removed,
            message=(
                f"Forgot '{args.name}'."
                if removed
                else f"No memory named '{args.name}' to forget."
            ),
        )

    @classmethod
    def format_call_display(cls, args: RememberArgs) -> ToolCallDisplay:
        verb = "Forgetting" if args.action == MemoryAction.DELETE else "Remembering"
        return ToolCallDisplay(summary=f"{verb} '{args.name}'")

    @classmethod
    def get_result_display(cls, event: ToolResultEvent) -> ToolResultDisplay:
        if not isinstance(event.result, RememberResult):
            return ToolResultDisplay(
                success=False, message=event.error or event.skip_reason or "No result"
            )
        return ToolResultDisplay(success=True, message=event.result.message)

    @classmethod
    def get_status_text(cls) -> str:
        return "Updating memory"
