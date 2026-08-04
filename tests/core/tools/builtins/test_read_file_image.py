from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import struct
import zlib

import pytest

from tests.mock.utils import collect_result
from vibe.core.config.harness_files import (
    init_harness_files_manager,
    reset_harness_files_manager,
)
from vibe.core.llm.format import APIToolFormatHandler, ResolvedToolCall
from vibe.core.tools.builtins.read_file import (
    ReadFile,
    ReadFileArgs,
    ReadFileResult,
    ReadFileState,
    ReadFileToolConfig,
)
from vibe.core.trusted_folders import trusted_folders_manager


@pytest.fixture()
def _setup_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(trusted_folders_manager, "is_trusted", lambda _: True)
    monkeypatch.setattr(
        trusted_folders_manager, "find_trust_root", lambda _: tmp_path.resolve()
    )
    reset_harness_files_manager()
    init_harness_files_manager("user", "project")
    yield
    reset_harness_files_manager()


def _make_read_file() -> ReadFile:
    return ReadFile(config_getter=lambda: ReadFileToolConfig(), state=ReadFileState())


def _write_png(path: Path) -> None:
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


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_manager")
async def test_read_image_attaches_data_url(tmp_path: Path) -> None:
    img = tmp_path / "pic.png"
    _write_png(img)
    tool = _make_read_file()

    result = await collect_result(tool.run(ReadFileArgs(path=str(img))))

    assert isinstance(result, ReadFileResult)
    assert result.image_urls is not None
    assert result.image_urls[0].startswith("data:image/png;base64,")
    assert "pic.png" in result.content
    assert tool.get_result_images(result) == result.image_urls


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_manager")
async def test_image_url_excluded_from_model_dump(tmp_path: Path) -> None:
    img = tmp_path / "pic.png"
    _write_png(img)
    tool = _make_read_file()

    result = await collect_result(tool.run(ReadFileArgs(path=str(img))))

    # The base64 must not leak into the text serialization sent to the LLM.
    assert "image_urls" not in result.model_dump()


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_manager")
async def test_read_text_file_has_no_image(tmp_path: Path) -> None:
    txt = tmp_path / "note.txt"
    txt.write_text("hello world", encoding="utf-8")
    tool = _make_read_file()

    result = await collect_result(tool.run(ReadFileArgs(path=str(txt))))

    assert result.image_urls is None
    assert tool.get_result_images(result) is None
    assert "hello world" in result.content


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_manager")
async def test_oversized_image_not_attached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("vibe.core.utils.images.MAX_IMAGE_BYTES", 1)
    img = tmp_path / "big.png"
    _write_png(img)
    tool = _make_read_file()

    result = await collect_result(tool.run(ReadFileArgs(path=str(img))))

    assert result.image_urls is None
    assert "could not be attached" in result.content


def test_tool_response_message_carries_images() -> None:
    handler = APIToolFormatHandler()
    call = ResolvedToolCall(
        tool_name="read_file",
        tool_class=ReadFile,
        validated_args=ReadFileArgs(path="p"),
    )
    msg = handler.create_tool_response_message(
        call, "[Image attached: pic.png]", images=["data:image/png;base64,AAAA"]
    )
    assert msg.images == ["data:image/png;base64,AAAA"]
    assert msg.role.value == "tool"
