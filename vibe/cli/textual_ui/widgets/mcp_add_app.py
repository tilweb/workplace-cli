from __future__ import annotations

from typing import ClassVar

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Vertical
from textual.message import Message
from textual.widgets import Input, Static

from vibe.cli.mcp_cli import McpCliError, add_server, build_server
from vibe.cli.textual_ui.widgets.no_markup_static import NoMarkupStatic
from vibe.cli.textual_ui.widgets.vscode_compat import VscodeCompatInput

# (field key, label, placeholder, default value)
_FIELDS: list[tuple[str, str, str, str]] = [
    ("name", "Name", "short alias, e.g. youtrack", ""),
    ("transport", "Transport", "streamable-http | http", "streamable-http"),
    ("url", "URL", "https://<instance>.youtrack.cloud/mcp", ""),
    ("api_key_env", "API key env var (optional)", "e.g. YOUTRACK_TOKEN", ""),
]


class McpAddApp(Container):
    can_focus = True
    can_focus_children = True

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("up", "focus_previous", "Up", show=False),
        Binding("down", "focus_next", "Down", show=False),
    ]

    class McpAddClosed(Message):
        def __init__(
            self, saved: bool, name: str | None = None, error: str | None = None
        ) -> None:
            super().__init__()
            self.saved = saved
            self.name = name
            self.error = error

    def __init__(self) -> None:
        super().__init__(id="mcpadd-app")
        self.inputs: dict[str, Input] = {}

    def compose(self) -> ComposeResult:
        with Vertical(id="mcpadd-content"):
            yield NoMarkupStatic("Add MCP Server", classes="settings-title")
            for key, label, placeholder, default in _FIELDS:
                yield Static(f"[bold ansi_blue]{label}[/]", classes="proxy-label-line")
                input_widget = VscodeCompatInput(
                    value=default,
                    placeholder=placeholder,
                    id=f"mcpadd-input-{key}",
                    classes="proxy-input",
                )
                self.inputs[key] = input_widget
                yield input_widget
            yield NoMarkupStatic(
                "↑↓ navigate  Enter save & exit  ESC cancel  "
                "(stdio servers: use `workplace mcp add … --transport stdio`)",
                classes="settings-help",
            )

    def focus(self, scroll_visible: bool = True) -> McpAddApp:
        if self.inputs:
            next(iter(self.inputs.values())).focus(scroll_visible=scroll_visible)
        else:
            super().focus(scroll_visible=scroll_visible)
        return self

    def action_focus_next(self) -> None:
        self._move_focus(1)

    def action_focus_previous(self) -> None:
        self._move_focus(-1)

    def _move_focus(self, delta: int) -> None:
        inputs = list(self.inputs.values())
        focused = self.screen.focused
        if isinstance(focused, Input) and focused in inputs:
            idx = (inputs.index(focused) + delta) % len(inputs)
            inputs[idx].focus()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self._save_and_close()

    def on_blur(self, _event: events.Blur) -> None:
        self.call_after_refresh(self._refocus_if_needed)

    def on_input_blurred(self, _event: Input.Blurred) -> None:
        self.call_after_refresh(self._refocus_if_needed)

    def _refocus_if_needed(self) -> None:
        if self.has_focus or any(inp.has_focus for inp in self.inputs.values()):
            return
        self.focus()

    def _save_and_close(self) -> None:
        values = {key: inp.value.strip() for key, inp in self.inputs.items()}
        try:
            server = build_server(
                name=values["name"],
                transport=values["transport"] or "streamable-http",
                url=values["url"] or None,
                api_key_env=values["api_key_env"],
                api_key_header="Authorization",
                api_key_format="Bearer {token}",
                headers={},
                env={},
                command_argv=[],
            )
            add_server(server)
        except (McpCliError, Exception) as exc:
            self.post_message(self.McpAddClosed(saved=False, error=str(exc)))
            return
        self.post_message(self.McpAddClosed(saved=True, name=server.name))

    def action_close(self) -> None:
        self.post_message(self.McpAddClosed(saved=False))
