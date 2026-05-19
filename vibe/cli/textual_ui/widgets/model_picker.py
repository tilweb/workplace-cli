from __future__ import annotations

from typing import Any, ClassVar, NamedTuple

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from vibe.cli.textual_ui.widgets.no_markup_static import NoMarkupStatic


class ModelEntry(NamedTuple):
    alias: str
    is_discovered: bool = False


def _build_option_text(entry: ModelEntry, is_current: bool) -> Text:
    text = Text(no_wrap=True)
    marker = "› " if is_current else "  "
    style = "bold" if is_current else ""
    text.append(marker, style="green" if is_current else "")
    text.append(entry.alias, style=style)
    if entry.is_discovered:
        text.append("  · live", style="dim")
    return text


def _build_provider_header(provider_name: str) -> Text:
    text = Text(no_wrap=True)
    text.append(provider_name.upper(), style="bold cyan")
    return text


_LOADING_HELP = "⟳ Refreshing models…  Esc Cancel"
_DEFAULT_HELP = "↑↓ Navigate  Enter Select  Esc Cancel"


class ModelPickerApp(Vertical):
    """Model picker bottom app for selecting the active model.

    Models are grouped by provider; each group is preceded by a disabled
    header option. Discovered (cache/runtime) entries get a "· live" suffix.
    """

    can_focus_children = True

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel", show=False)
    ]

    class ModelSelected(Message):
        def __init__(self, alias: str) -> None:
            self.alias = alias
            super().__init__()

    class Cancelled(Message):
        pass

    def __init__(
        self,
        models_by_provider: dict[str, list[ModelEntry]],
        current_model: str,
        *,
        loading: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(id="modelpicker-app", **kwargs)
        self._models_by_provider = models_by_provider
        self._current_model = current_model
        self._loading = loading

    def compose(self) -> ComposeResult:
        with Vertical(id="modelpicker-content"):
            yield NoMarkupStatic("Select Model", classes="modelpicker-title")
            yield OptionList(*self._build_options(), id="modelpicker-options")
            yield NoMarkupStatic(
                _LOADING_HELP if self._loading else _DEFAULT_HELP,
                id="modelpicker-help",
                classes="modelpicker-help",
            )

    def _build_options(self) -> list[Option]:
        options: list[Option] = []
        for provider_name, entries in self._models_by_provider.items():
            if not entries:
                continue
            header_id = f"__header__{provider_name}"
            options.append(
                Option(
                    _build_provider_header(provider_name), id=header_id, disabled=True
                )
            )
            for entry in entries:
                options.append(
                    Option(
                        _build_option_text(entry, entry.alias == self._current_model),
                        id=entry.alias,
                    )
                )
        return options

    def on_mount(self) -> None:
        option_list = self.query_one(OptionList)
        self._highlight_current(option_list)
        option_list.focus()

    def _highlight_current(self, option_list: OptionList) -> None:
        for i, option in enumerate(option_list._options):
            if option.id == self._current_model:
                option_list.highlighted = i
                return
        # Otherwise highlight the first non-disabled (i.e. first real model)
        for i, option in enumerate(option_list._options):
            if not option.disabled:
                option_list.highlighted = i
                return

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id and not event.option.disabled:
            self.post_message(self.ModelSelected(event.option.id))

    def action_cancel(self) -> None:
        self.post_message(self.Cancelled())

    def update_models(
        self,
        models_by_provider: dict[str, list[ModelEntry]],
        *,
        loading: bool = False,
    ) -> None:
        """Refresh the picker contents in place (e.g. after async discovery).

        Preserves the current selection if it still exists in the new list.
        """
        self._models_by_provider = models_by_provider
        self._loading = loading
        option_list = self.query_one(OptionList)
        option_list.clear_options()
        option_list.add_options(self._build_options())
        self._highlight_current(option_list)
        help_widget = self.query_one("#modelpicker-help", NoMarkupStatic)
        help_widget.update(_LOADING_HELP if loading else _DEFAULT_HELP)
