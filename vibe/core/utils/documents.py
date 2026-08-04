from __future__ import annotations

import base64
import io
from pathlib import Path

from vibe.core.logger import logger

# === ADACOR PATCH: document (PDF) support via page rendering (vision) ===

# Pages beyond this are not rendered (token/latency cap). PDFs render at this
# scale (72dpi * scale); 2.0 keeps text legible without huge images.
MAX_PDF_PAGES = 10
PDF_RENDER_SCALE = 2
MAX_PDF_BYTES = 25 * 1024 * 1024


def is_pdf_path(path: Path) -> bool:
    return path.suffix.lower() == ".pdf"


def render_pdf_to_data_urls(
    path: Path, *, max_pages: int = MAX_PDF_PAGES, scale: int = PDF_RENDER_SCALE
) -> list[str]:
    """Render the first pages of a PDF to PNG ``data:`` URLs.

    Returns an empty list if the file is missing, too large, or cannot be
    rendered (e.g. pypdfium2/Pillow unavailable or a corrupt PDF).
    """
    try:
        if path.stat().st_size > MAX_PDF_BYTES:
            return []
        raw = path.read_bytes()
    except OSError:
        return []

    try:
        import pypdfium2 as pdfium
    except ImportError:
        logger.warning("pypdfium2 not installed — cannot render PDF %s", path)
        return []

    urls: list[str] = []
    try:
        doc = pdfium.PdfDocument(raw)
        try:
            for i in range(min(len(doc), max_pages)):
                pil = doc[i].render(scale=scale).to_pil().convert("RGB")
                out = io.BytesIO()
                pil.save(out, format="PNG")
                encoded = base64.b64encode(out.getvalue()).decode("ascii")
                urls.append(f"data:image/png;base64,{encoded}")
        finally:
            doc.close()
    except Exception as exc:
        logger.warning("Failed to render PDF %s: %s", path, exc)
        return []

    return urls
