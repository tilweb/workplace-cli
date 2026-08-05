from __future__ import annotations

import os

import pytest

from tests.mock.utils import collect_result
from vibe.core.tools.base import BaseToolState, ToolError
from vibe.core.tools.builtins.glob import Glob, GlobArgs, GlobToolConfig


@pytest.fixture
def glob_tool(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = GlobToolConfig()
    return Glob(config_getter=lambda: config, state=BaseToolState())


@pytest.mark.asyncio
async def test_recursive_match(glob_tool, tmp_path):
    (tmp_path / "a.py").write_text("x")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.py").write_text("x")
    (tmp_path / "c.txt").write_text("x")

    result = await collect_result(glob_tool.run(GlobArgs(pattern="**/*.py")))

    paths = result.paths.splitlines()
    assert result.match_count == 2
    assert any(p.endswith("a.py") for p in paths)
    assert any(p.endswith("b.py") for p in paths)
    assert not any(p.endswith("c.txt") for p in paths)


@pytest.mark.asyncio
async def test_non_recursive_pattern_stays_top_level(glob_tool, tmp_path):
    (tmp_path / "a.py").write_text("x")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.py").write_text("x")

    result = await collect_result(glob_tool.run(GlobArgs(pattern="*.py")))

    assert result.match_count == 1
    assert result.paths.endswith("a.py")


@pytest.mark.asyncio
async def test_excludes_default_dirs(glob_tool, tmp_path):
    (tmp_path / "keep.py").write_text("x")
    for bad in ("node_modules", ".git", "__pycache__"):
        d = tmp_path / bad
        d.mkdir()
        (d / "skip.py").write_text("x")

    result = await collect_result(glob_tool.run(GlobArgs(pattern="**/*.py")))

    assert result.match_count == 1
    assert "skip.py" not in result.paths
    assert "keep.py" in result.paths


@pytest.mark.asyncio
async def test_sorts_by_mtime_newest_first(glob_tool, tmp_path):
    old = tmp_path / "old.py"
    new = tmp_path / "new.py"
    old.write_text("x")
    new.write_text("x")
    os.utime(old, (1_000_000, 1_000_000))
    os.utime(new, (2_000_000, 2_000_000))

    result = await collect_result(glob_tool.run(GlobArgs(pattern="*.py")))

    lines = result.paths.splitlines()
    assert lines[0].endswith("new.py")
    assert lines[1].endswith("old.py")


@pytest.mark.asyncio
async def test_truncates_to_max_results(glob_tool, tmp_path):
    for i in range(10):
        (tmp_path / f"f{i}.py").write_text("x")

    result = await collect_result(
        glob_tool.run(GlobArgs(pattern="*.py", max_results=3))
    )

    assert result.match_count == 3
    assert result.was_truncated


@pytest.mark.asyncio
async def test_empty_pattern_raises(glob_tool):
    with pytest.raises(ToolError) as err:
        await collect_result(glob_tool.run(GlobArgs(pattern="   ")))
    assert "Empty glob pattern" in str(err.value)


@pytest.mark.asyncio
async def test_nonexistent_path_raises(glob_tool):
    with pytest.raises(ToolError) as err:
        await collect_result(glob_tool.run(GlobArgs(pattern="*.py", path="nope")))
    assert "does not exist" in str(err.value)


@pytest.mark.asyncio
async def test_path_that_is_a_file_raises(glob_tool, tmp_path):
    f = tmp_path / "file.py"
    f.write_text("x")
    with pytest.raises(ToolError) as err:
        await collect_result(glob_tool.run(GlobArgs(pattern="*", path="file.py")))
    assert "not a directory" in str(err.value)


@pytest.mark.asyncio
async def test_directories_are_not_returned(glob_tool, tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("x")

    result = await collect_result(glob_tool.run(GlobArgs(pattern="**/*")))

    assert result.match_count == 1
    assert result.paths.endswith("mod.py")
