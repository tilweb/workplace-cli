from __future__ import annotations

from pathlib import Path

from vibe.core.paths._local_config_walk import (
    _MAX_DIRS,
    WALK_MAX_DEPTH,
    walk_local_config_dirs,
)


class TestWalkTools:
    def test_finds_config_at_root(self, tmp_path: Path) -> None:
        (tmp_path / ".workplace" / "tools").mkdir(parents=True)
        result = walk_local_config_dirs(tmp_path)
        assert tmp_path.resolve() / ".workplace" / "tools" in result.tools

    def test_finds_config_within_depth_limit(self, tmp_path: Path) -> None:
        nested = tmp_path
        for i in range(WALK_MAX_DEPTH):
            nested = nested / f"level{i}"
        (nested / ".workplace" / "skills").mkdir(parents=True)
        result = walk_local_config_dirs(tmp_path)
        assert nested.resolve() / ".workplace" / "skills" in result.skills

    def test_does_not_find_config_beyond_depth_limit(self, tmp_path: Path) -> None:
        nested = tmp_path
        for i in range(WALK_MAX_DEPTH + 1):
            nested = nested / f"level{i}"
        (nested / ".workplace" / "tools").mkdir(parents=True)
        result = walk_local_config_dirs(tmp_path)
        assert not result.tools
        assert not result.skills
        assert not result.agents

    def test_respects_dir_count_limit(self, tmp_path: Path) -> None:
        for i in range(_MAX_DIRS + 10):
            (tmp_path / f"dir{i:05d}").mkdir()
        (tmp_path / "zzz_last" / ".workplace" / "tools").mkdir(parents=True)
        result = walk_local_config_dirs(tmp_path)
        assert isinstance(result.tools, tuple)

    def test_skips_ignored_directories(self, tmp_path: Path) -> None:
        (tmp_path / "node_modules" / ".workplace" / "tools").mkdir(parents=True)
        (tmp_path / ".workplace" / "tools").mkdir(parents=True)
        result = walk_local_config_dirs(tmp_path)
        assert result.tools == (tmp_path.resolve() / ".workplace" / "tools",)

    def test_skips_dot_directories(self, tmp_path: Path) -> None:
        (tmp_path / ".hidden" / ".workplace" / "tools").mkdir(parents=True)
        result = walk_local_config_dirs(tmp_path)
        assert not result.tools

    def test_preserves_alphabetical_ordering(self, tmp_path: Path) -> None:
        (tmp_path / "bbb" / ".workplace" / "tools").mkdir(parents=True)
        (tmp_path / "aaa" / ".workplace" / "tools").mkdir(parents=True)
        (tmp_path / ".workplace" / "tools").mkdir(parents=True)
        result = walk_local_config_dirs(tmp_path)
        resolved = tmp_path.resolve()
        assert result.tools == (
            resolved / ".workplace" / "tools",
            resolved / "aaa" / ".workplace" / "tools",
            resolved / "bbb" / ".workplace" / "tools",
        )

    def test_finds_agents_skills(self, tmp_path: Path) -> None:
        (tmp_path / ".agents" / "skills").mkdir(parents=True)
        result = walk_local_config_dirs(tmp_path)
        assert tmp_path.resolve() / ".agents" / "skills" in result.skills

    def test_finds_all_config_types(self, tmp_path: Path) -> None:
        (tmp_path / ".workplace" / "tools").mkdir(parents=True)
        (tmp_path / ".workplace" / "skills").mkdir(parents=True)
        (tmp_path / ".workplace" / "agents").mkdir(parents=True)
        (tmp_path / ".agents" / "skills").mkdir(parents=True)
        result = walk_local_config_dirs(tmp_path)
        resolved = tmp_path.resolve()
        assert resolved / ".workplace" / "tools" in result.tools
        assert resolved / ".workplace" / "skills" in result.skills
        assert resolved / ".workplace" / "agents" in result.agents
        assert resolved / ".agents" / "skills" in result.skills


class TestWalkConfigDirs:
    def test_finds_vibe_with_tools(self, tmp_path: Path) -> None:
        (tmp_path / ".workplace" / "tools").mkdir(parents=True)
        result = walk_local_config_dirs(tmp_path)
        assert tmp_path.resolve() / ".workplace" in result.config_dirs

    def test_finds_vibe_with_skills(self, tmp_path: Path) -> None:
        (tmp_path / ".workplace" / "skills").mkdir(parents=True)
        result = walk_local_config_dirs(tmp_path)
        assert tmp_path.resolve() / ".workplace" in result.config_dirs

    def test_finds_agents_with_skills(self, tmp_path: Path) -> None:
        (tmp_path / ".agents" / "skills").mkdir(parents=True)
        result = walk_local_config_dirs(tmp_path)
        assert tmp_path.resolve() / ".agents" in result.config_dirs

    def test_ignores_empty_vibe_dir(self, tmp_path: Path) -> None:
        (tmp_path / ".workplace").mkdir()
        result = walk_local_config_dirs(tmp_path)
        assert result.config_dirs == ()

    def test_ignores_empty_agents_dir(self, tmp_path: Path) -> None:
        (tmp_path / ".agents").mkdir()
        result = walk_local_config_dirs(tmp_path)
        assert result.config_dirs == ()

    def test_returns_empty_when_empty(self, tmp_path: Path) -> None:
        result = walk_local_config_dirs(tmp_path)
        assert result.config_dirs == ()

    def test_finds_shallow_nested(self, tmp_path: Path) -> None:
        (tmp_path / "sub" / ".workplace" / "skills").mkdir(parents=True)
        result = walk_local_config_dirs(tmp_path)
        assert tmp_path.resolve() / "sub" / ".workplace" in result.config_dirs

    def test_finds_at_depth_2(self, tmp_path: Path) -> None:
        (tmp_path / "a" / "b" / ".agents" / "skills").mkdir(parents=True)
        result = walk_local_config_dirs(tmp_path)
        assert tmp_path.resolve() / "a" / "b" / ".agents" in result.config_dirs

    def test_returns_empty_beyond_default_depth(self, tmp_path: Path) -> None:
        (tmp_path / "a" / "b" / "c" / "d" / "e" / ".workplace" / "tools").mkdir(
            parents=True
        )
        result = walk_local_config_dirs(tmp_path)
        assert result.config_dirs == ()

    def test_custom_depth(self, tmp_path: Path) -> None:
        (tmp_path / "a" / "b" / "c" / "d" / "e" / ".workplace" / "tools").mkdir(
            parents=True
        )
        result = walk_local_config_dirs(tmp_path, max_depth=5)
        assert (
            tmp_path.resolve() / "a" / "b" / "c" / "d" / "e" / ".workplace"
            in result.config_dirs
        )

    def test_finds_match_among_many_dirs(self, tmp_path: Path) -> None:
        (tmp_path / ".workplace" / "tools").mkdir(parents=True)
        for i in range(100):
            (tmp_path / f"dir{i}").mkdir()
        result = walk_local_config_dirs(tmp_path)
        assert tmp_path.resolve() / ".workplace" in result.config_dirs

    def test_skips_ignored_directories(self, tmp_path: Path) -> None:
        (tmp_path / "node_modules" / ".workplace" / "skills").mkdir(parents=True)
        result = walk_local_config_dirs(tmp_path)
        assert result.config_dirs == ()

    def test_finds_vibe_with_prompts(self, tmp_path: Path) -> None:
        (tmp_path / ".workplace" / "prompts").mkdir(parents=True)
        result = walk_local_config_dirs(tmp_path)
        assert tmp_path.resolve() / ".workplace" in result.config_dirs

    def test_finds_vibe_with_config_toml(self, tmp_path: Path) -> None:
        (tmp_path / ".workplace").mkdir()
        (tmp_path / ".workplace" / "config.toml").write_text("")
        result = walk_local_config_dirs(tmp_path)
        assert tmp_path.resolve() / ".workplace" in result.config_dirs

    def test_finds_multiple_config_dirs(self, tmp_path: Path) -> None:
        (tmp_path / ".workplace" / "skills").mkdir(parents=True)
        (tmp_path / ".agents" / "skills").mkdir(parents=True)
        (tmp_path / "sub" / ".workplace" / "tools").mkdir(parents=True)
        result = walk_local_config_dirs(tmp_path)
        resolved = tmp_path.resolve()
        assert resolved / ".workplace" in result.config_dirs
        assert resolved / ".agents" in result.config_dirs
        assert resolved / "sub" / ".workplace" in result.config_dirs
