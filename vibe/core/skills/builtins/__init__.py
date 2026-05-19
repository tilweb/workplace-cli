from __future__ import annotations

from vibe.core.skills.builtins.brand_guidelines import SKILL as BRAND_GUIDELINES_SKILL
from vibe.core.skills.builtins.canvas_design import SKILL as CANVAS_DESIGN_SKILL
from vibe.core.skills.builtins.frontend_design import SKILL as FRONTEND_DESIGN_SKILL
from vibe.core.skills.builtins.skill_creator import SKILL as SKILL_CREATOR_SKILL
from vibe.core.skills.builtins.theme_factory import SKILL as THEME_FACTORY_SKILL
from vibe.core.skills.builtins.vibe import SKILL as VIBE_SKILL
from vibe.core.skills.models import SkillInfo

BUILTIN_SKILLS: dict[str, SkillInfo] = {
    skill.name: skill
    for skill in [
        VIBE_SKILL,
        FRONTEND_DESIGN_SKILL,
        BRAND_GUIDELINES_SKILL,
        CANVAS_DESIGN_SKILL,
        THEME_FACTORY_SKILL,
        SKILL_CREATOR_SKILL,
    ]
}
