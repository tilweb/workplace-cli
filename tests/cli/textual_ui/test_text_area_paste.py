from __future__ import annotations

from pathlib import Path

from vibe.cli.textual_ui.widgets.chat_input.text_area import (
    DRAG_FOLDER_MESSAGE,
    DRAG_TOO_MANY_MESSAGE,
    path_to_mention,
    resolve_dropped_file,
)


def test_single_dropped_file_returns_path(tmp_path: Path) -> None:
    f = tmp_path / "report.pdf"
    f.write_bytes(b"x")

    assert resolve_dropped_file(str(f)) == f


def test_dropped_file_with_spaces_is_parsed(tmp_path: Path) -> None:
    f = tmp_path / "my report.pdf"
    f.write_bytes(b"x")

    # Terminals escape spaces on drag (path\ with\ spaces).
    escaped = str(f).replace(" ", "\\ ")
    assert resolve_dropped_file(escaped) == f


def test_dropped_folder_is_rejected(tmp_path: Path) -> None:
    assert resolve_dropped_file(str(tmp_path)) == DRAG_FOLDER_MESSAGE


def test_multiple_dropped_files_are_rejected(tmp_path: Path) -> None:
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    a.write_bytes(b"x")
    b.write_bytes(b"x")

    assert resolve_dropped_file(f"{a} {b}") == DRAG_TOO_MANY_MESSAGE


def test_ordinary_text_falls_through() -> None:
    assert resolve_dropped_file("just some pasted text") is None


def test_relative_word_that_exists_falls_through(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "README").write_text("hi")
    monkeypatch.chdir(tmp_path)
    # A bare relative word must not be treated as a drop (not absolute).
    assert resolve_dropped_file("README") is None


def test_nonexistent_absolute_path_falls_through() -> None:
    assert resolve_dropped_file("/nope/does/not/exist.png") is None


def test_path_to_mention_plain() -> None:
    assert path_to_mention(Path("/a/b/c.png")) == "@/a/b/c.png "


def test_path_to_mention_quotes_spaces() -> None:
    assert path_to_mention(Path("/a/b/my file.pdf")) == '@"/a/b/my file.pdf" '


# --- integration: the _on_paste wiring inside the running app ---

import pytest
from textual import events

from vibe.cli.textual_ui.widgets.chat_input.text_area import ChatTextArea


@pytest.mark.asyncio
async def test_paste_single_file_inserts_mention(vibe_app, tmp_path: Path) -> None:
    f = tmp_path / "shot.png"
    f.write_bytes(b"x")
    async with vibe_app.run_test():
        ta = vibe_app.query_one(ChatTextArea)
        await ta._on_paste(events.Paste(str(f)))
        assert ta.text == f"@{f} "


@pytest.mark.asyncio
async def test_paste_folder_inserts_nothing(vibe_app, tmp_path: Path) -> None:
    async with vibe_app.run_test():
        ta = vibe_app.query_one(ChatTextArea)
        await ta._on_paste(events.Paste(str(tmp_path)))
        assert ta.text == ""


@pytest.mark.asyncio
async def test_paste_ordinary_text_is_inserted(vibe_app) -> None:
    async with vibe_app.run_test():
        ta = vibe_app.query_one(ChatTextArea)
        await ta._on_paste(events.Paste("hello world"))
        assert ta.text == "hello world"
