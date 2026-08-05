"""Guards for the document-builder skill.

The skill has no logic of its own — it instructs the model to write a Python
script using bundled libraries. These tests protect the two things that would
silently break it: the skill being wired into the registry, and the four
document libraries remaining installed.
"""

from __future__ import annotations

import importlib

import pytest

from vibe.core.skills.builtins import BUILTIN_SKILLS


def test_skill_is_registered_and_user_invocable():
    skill = BUILTIN_SKILLS.get("document-builder")
    assert skill is not None
    assert skill.user_invocable is True
    assert skill.prompt.strip()


@pytest.mark.parametrize("module", ["docx", "openpyxl", "pptx", "reportlab"])
def test_document_libraries_are_importable(module):
    # If a dependency is dropped from pyproject, the skill becomes a dead letter.
    assert importlib.import_module(module) is not None


def test_prompt_mentions_all_four_formats():
    prompt = BUILTIN_SKILLS["document-builder"].prompt.lower()
    for token in (".docx", ".xlsx", ".pptx", "pdf"):
        assert token in prompt
