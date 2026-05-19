"""ADACOR: Textual theme name compatibility shim (no upstream equivalent).

Upstream sets `self.theme = "textual-ansi"` in three places (the main app,
the onboarding flow, and the trusted-folder dialog). That theme name exists
in Textual 8.2.4 (our pinned version) but was renamed to `ansi-dark` /
`ansi-light` in 8.2.5. When `uv tool install` resolves to a newer Textual,
the original assignment crashes with `InvalidThemeError`.

This helper returns the best available ANSI theme for whichever Textual
version is installed, with a safe builtin fallback so the app starts even
on theme renames we don't know about yet.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from textual.app import App

_ANSI_CANDIDATES = ("textual-ansi", "ansi-dark")
_FALLBACK = "textual-dark"  # always present as a built-in


def select_ansi_theme(app: App) -> str:
    registered = app._registered_themes
    for name in _ANSI_CANDIDATES:
        if name in registered:
            return name
    return _FALLBACK
