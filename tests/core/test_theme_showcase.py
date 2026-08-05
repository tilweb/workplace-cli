from __future__ import annotations

import importlib.util
from types import ModuleType

from vibe.core.skills.builtins import BUILTIN_SKILLS
from vibe.core.skills.builtins.theme_factory import THEME_SHOWCASE_PATH


def _load_generator() -> ModuleType:
    path = THEME_SHOWCASE_PATH.parent / "build_theme_showcase.py"
    spec = importlib.util.spec_from_file_location("theme_showcase_gen", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_showcase_asset_is_shipped():
    assert THEME_SHOWCASE_PATH.exists()
    assert THEME_SHOWCASE_PATH.read_bytes().startswith(b"%PDF")


def test_skill_prompt_points_at_the_asset():
    prompt = BUILTIN_SKILLS["theme-factory"].prompt
    assert str(THEME_SHOWCASE_PATH) in prompt


def test_generator_data_matches_skill_prompt():
    # Guard against drift between the visual showcase and the theme definitions
    # embedded in the skill prompt.
    generator = _load_generator()
    prompt = BUILTIN_SKILLS["theme-factory"].prompt
    assert len(generator.THEMES) == 10
    for name, _desc, palette, _headers, _body, _best in generator.THEMES:
        assert name in prompt, f"theme {name!r} missing from skill prompt"
        for _color_name, hex_code in palette:
            assert hex_code in prompt, f"{hex_code} missing from skill prompt"


def test_generator_produces_valid_pdf(tmp_path):
    generator = _load_generator()
    out = generator.build(tmp_path / "showcase.pdf")
    assert out.exists()
    assert out.read_bytes().startswith(b"%PDF")
