from __future__ import annotations

from pathlib import Path

import pytest

from vibe.core.memory import MemoryManager, MemoryStoreError


def _manager(tmp_path: Path) -> MemoryManager:
    return MemoryManager(memory_dir=tmp_path / "memory")


def test_empty_store_has_no_index(tmp_path: Path) -> None:
    m = _manager(tmp_path)
    assert m.load_index() is None
    assert m.list_memories() == []


def test_write_creates_file_and_index(tmp_path: Path) -> None:
    m = _manager(tmp_path)
    path = m.write_memory("deploy", "Deploy via make ship.", "How to deploy")

    assert path.exists()
    assert m.list_memories() == ["deploy"]
    index = m.load_index() or ""
    assert "[deploy](deploy.md)" in index
    assert "How to deploy" in index
    stored = m.read_memory("deploy") or ""
    assert "name: deploy" in stored
    assert "Deploy via make ship." in stored


def test_overwrite_does_not_duplicate_index_line(tmp_path: Path) -> None:
    m = _manager(tmp_path)
    m.write_memory("lang", "German.", "Language")
    m.write_memory("lang", "German, code in English.", "Language (updated)")

    index = m.load_index() or ""
    assert index.count("(lang.md)") == 1
    assert "updated" in index


def test_delete_removes_memory_and_index_when_last(tmp_path: Path) -> None:
    m = _manager(tmp_path)
    m.write_memory("a", "fact a", "desc a")
    assert m.delete_memory("a") is True
    assert m.delete_memory("a") is False
    assert m.load_index() is None
    assert not m.index_path.exists()


def test_index_survives_partial_delete(tmp_path: Path) -> None:
    m = _manager(tmp_path)
    m.write_memory("a", "fact a", "desc a")
    m.write_memory("b", "fact b", "desc b")
    m.delete_memory("a")

    index = m.load_index() or ""
    assert "(a.md)" not in index
    assert "(b.md)" in index


@pytest.mark.parametrize("bad", ["Bad Name", "", "a/b", "under_score", "x" * 65])
def test_invalid_slug_rejected(tmp_path: Path, bad: str) -> None:
    m = _manager(tmp_path)
    with pytest.raises(MemoryStoreError):
        m.write_memory(bad, "content", "desc")


@pytest.mark.parametrize(("content", "desc"), [("", "desc"), ("body", "")])
def test_empty_content_or_description_rejected(
    tmp_path: Path, content: str, desc: str
) -> None:
    m = _manager(tmp_path)
    with pytest.raises(MemoryStoreError):
        m.write_memory("slug", content, desc)
