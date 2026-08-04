from __future__ import annotations

import json
from pathlib import Path
import struct
import zlib

from tests.conftest import build_test_agent_loop, build_test_vibe_config
from vibe.core.config import ModelConfig, ProviderConfig
from vibe.core.llm.backend.generic import OpenAIAdapter
from vibe.core.llm.message_utils import merge_consecutive_user_messages
from vibe.core.types import Backend, LLMMessage, Role
from vibe.core.utils.images import build_image_data_url, is_image_path

_DATA_URL = "data:image/png;base64,AAAA"
_PROVIDER = ProviderConfig(
    name="adacor", api_base="https://api.adacor.ai/x/v1", backend=Backend.GENERIC
)


def _tiny_png(path: Path) -> None:
    w = h = 2
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * w for _ in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return (
            struct.pack(">I", len(data))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _prepare(messages: list[LLMMessage]) -> dict:
    prepared = OpenAIAdapter().prepare_request(
        model_name="qwen3.5-35b",
        messages=messages,
        temperature=0.2,
        tools=None,
        max_tokens=None,
        tool_choice=None,
        enable_streaming=False,
        provider=_PROVIDER,
    )
    return json.loads(prepared.body)


def test_is_image_path() -> None:
    assert is_image_path(Path("a.png")) is True
    assert is_image_path(Path("a.JPG")) is True
    assert is_image_path(Path("a.txt")) is False


def test_build_image_data_url_for_real_png(tmp_path: Path) -> None:
    img = tmp_path / "pic.png"
    _tiny_png(img)
    url = build_image_data_url(img)
    assert url is not None
    assert url.startswith("data:image/png;base64,")


def test_build_image_data_url_none_for_non_image(tmp_path: Path) -> None:
    txt = tmp_path / "a.txt"
    txt.write_text("hello")
    assert build_image_data_url(txt) is None


def test_build_image_data_url_none_for_missing(tmp_path: Path) -> None:
    assert build_image_data_url(tmp_path / "missing.png") is None


def test_user_message_with_images_serializes_to_multimodal_content() -> None:
    body = _prepare([LLMMessage(role=Role.user, content="was?", images=[_DATA_URL])])
    content = body["messages"][0]["content"]
    assert content == [
        {"type": "text", "text": "was?"},
        {"type": "image_url", "image_url": {"url": _DATA_URL}},
    ]
    assert "images" not in body["messages"][0]


def test_message_without_images_keeps_string_content() -> None:
    body = _prepare([LLMMessage(role=Role.user, content="hi")])
    assert body["messages"][0]["content"] == "hi"
    assert "images" not in body["messages"][0]


def test_images_only_message_has_no_text_part() -> None:
    body = _prepare([LLMMessage(role=Role.user, content=None, images=[_DATA_URL])])
    assert body["messages"][0]["content"] == [
        {"type": "image_url", "image_url": {"url": _DATA_URL}}
    ]


def test_merge_consecutive_user_messages_preserves_images() -> None:
    merged = merge_consecutive_user_messages([
        LLMMessage(role=Role.user, content="a", images=[_DATA_URL]),
        LLMMessage(role=Role.user, content="b", images=["data:image/png;base64,BBBB"]),
    ])
    assert len(merged) == 1
    assert merged[0].images == [_DATA_URL, "data:image/png;base64,BBBB"]


def test_add_concatenates_images() -> None:
    combined = LLMMessage(role=Role.user, content="a", images=[_DATA_URL]) + LLMMessage(
        role=Role.user, content="b"
    )
    assert combined.images == [_DATA_URL]


def _agent_with_vision(supports_vision: bool):
    cfg = build_test_vibe_config(
        active_model="m",
        models=[
            ModelConfig(
                name="m", provider="adacor", alias="m", supports_vision=supports_vision
            )
        ],
        providers=[_PROVIDER],
    )
    return build_test_agent_loop(config=cfg)


def test_images_kept_for_vision_model() -> None:
    agent = _agent_with_vision(True)
    assert agent._images_for_active_model([_DATA_URL]) == [_DATA_URL]


def test_images_dropped_for_non_vision_model() -> None:
    agent = _agent_with_vision(False)
    assert agent._images_for_active_model([_DATA_URL]) is None
