from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pypdfium2  # noqa: F401  # force native lib load before sys.platform is mocked
import pytest

from tests.mock.utils import collect_result
from vibe.core.config.harness_files import (
    init_harness_files_manager,
    reset_harness_files_manager,
)
from vibe.core.tools.builtins.read_file import (
    ReadFile,
    ReadFileArgs,
    ReadFileResult,
    ReadFileState,
    ReadFileToolConfig,
)
from vibe.core.trusted_folders import trusted_folders_manager
from vibe.core.utils.documents import render_pdf_to_data_urls


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


def _write_pdf(path: Path, pages: int) -> None:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument.new()
    for _ in range(pages):
        doc.new_page(200, 200)
    doc.save(str(path))
    doc.close()


def _make_read_file() -> ReadFile:
    return ReadFile(config_getter=lambda: ReadFileToolConfig(), state=ReadFileState())


def test_render_pdf_to_data_urls_returns_one_per_page(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    _write_pdf(pdf, pages=3)

    urls = render_pdf_to_data_urls(pdf)

    assert len(urls) == 3
    assert all(u.startswith("data:image/png;base64,") for u in urls)


def test_render_pdf_respects_max_pages(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    _write_pdf(pdf, pages=5)

    urls = render_pdf_to_data_urls(pdf, max_pages=2)

    assert len(urls) == 2


def test_render_missing_pdf_returns_empty(tmp_path: Path) -> None:
    assert render_pdf_to_data_urls(tmp_path / "missing.pdf") == []


def test_render_corrupt_pdf_returns_empty(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 not really a pdf")
    assert render_pdf_to_data_urls(bad) == []


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_manager")
async def test_read_pdf_attaches_page_images(tmp_path: Path) -> None:
    pdf = tmp_path / "report.pdf"
    _write_pdf(pdf, pages=2)
    tool = _make_read_file()

    result = await collect_result(tool.run(ReadFileArgs(path=str(pdf))))

    assert isinstance(result, ReadFileResult)
    assert result.image_urls is not None
    assert len(result.image_urls) == 2
    assert "PDF attached" in result.content
    assert tool.get_result_images(result) == result.image_urls
    assert "image_urls" not in result.model_dump()


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_manager")
async def test_read_unreadable_pdf_reports_placeholder(tmp_path: Path) -> None:
    pdf = tmp_path / "broken.pdf"
    pdf.write_bytes(b"%PDF-1.4 broken")
    tool = _make_read_file()

    result = await collect_result(tool.run(ReadFileArgs(path=str(pdf))))

    assert result.image_urls is None
    assert "could not be rendered" in result.content
