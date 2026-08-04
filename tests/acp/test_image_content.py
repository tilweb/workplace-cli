from __future__ import annotations

from acp.schema import ImageContentBlock, TextContentBlock

from vibe.acp.acp_agent_loop import VibeAcpAgentLoop


def test_build_images_extracts_image_blocks() -> None:
    agent = VibeAcpAgentLoop()
    blocks = [
        TextContentBlock(type="text", text="What is this?"),
        ImageContentBlock(type="image", data="QUJD", mime_type="image/png"),
    ]

    assert agent._build_images(blocks) == ["data:image/png;base64,QUJD"]


def test_build_images_empty_without_image_blocks() -> None:
    agent = VibeAcpAgentLoop()

    assert agent._build_images([TextContentBlock(type="text", text="hi")]) == []


def test_build_images_multiple() -> None:
    agent = VibeAcpAgentLoop()
    blocks = [
        ImageContentBlock(type="image", data="AAAA", mime_type="image/png"),
        ImageContentBlock(type="image", data="BBBB", mime_type="image/jpeg"),
    ]

    assert agent._build_images(blocks) == [
        "data:image/png;base64,AAAA",
        "data:image/jpeg;base64,BBBB",
    ]
