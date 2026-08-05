"""Guards that the visual design skills stay wired to the screenshot tool.

Both skills produce visual output; without a render-and-look-at-it step the
model judges design from source alone, and canvas-design in particular used to
be vague about how to produce the file at all.
"""

from __future__ import annotations

import pytest

from vibe.core.skills.builtins import BUILTIN_SKILLS


@pytest.mark.parametrize("skill_name", ["frontend-design", "canvas-design"])
def test_design_skill_uses_screenshot_for_visual_check(skill_name):
    prompt = BUILTIN_SKILLS[skill_name].prompt
    assert "screenshot" in prompt


def test_canvas_design_avoids_bare_python_for_pdf():
    # PDF rendering must use the venv interpreter, not the login shell's python.
    prompt = BUILTIN_SKILLS["canvas-design"].prompt
    assert "$WORKPLACE_PYTHON" in prompt
