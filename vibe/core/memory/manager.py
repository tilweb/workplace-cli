"""Persistent, cross-session memory store.

Each memory is a single Markdown file (``<slug>.md``) under the user's
memory directory (``$WORKPLACE_HOME/memory``), carrying a small frontmatter
header (name + description) followed by the remembered fact. A ``MEMORY.md``
index — one line per memory — is regenerated from the files on every write
or delete, so it can never drift from what is actually stored.

The index is injected into the system prompt each session, giving the agent
a durable, self-updating memory the way a coding assistant remembers user
preferences and project facts across runs.
"""

from __future__ import annotations

from pathlib import Path
import re

from vibe.core.logger import logger
from vibe.core.paths import MEMORY_DIR

_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_MAX_SLUG_LEN = 64
_INDEX_NAME = "MEMORY.md"
_INDEX_HEADER = (
    "# Memory Index\n\n"
    "Facts Workplace CLI remembers across sessions. One line per memory; "
    "read the linked file for the full note.\n"
)
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)


class MemoryStoreError(Exception):
    """Raised when a memory cannot be written, read, or deleted."""


class MemoryManager:
    """Reads and writes the user's persistent memory files and index."""

    def __init__(self, memory_dir: Path | None = None) -> None:
        self._dir = memory_dir if memory_dir is not None else MEMORY_DIR.path

    @property
    def directory(self) -> Path:
        return self._dir

    @property
    def index_path(self) -> Path:
        return self._dir / _INDEX_NAME

    def memory_path(self, name: str) -> Path:
        return self._dir / f"{self._validate_slug(name)}.md"

    @staticmethod
    def _validate_slug(name: str) -> str:
        slug = name.strip().lower()
        if not slug or len(slug) > _MAX_SLUG_LEN or not _SLUG_RE.match(slug):
            raise MemoryStoreError(
                f"Invalid memory name {name!r}. Use lowercase letters, numbers "
                "and hyphens (kebab-case), e.g. 'deploy-command'."
            )
        return slug

    def load_index(self) -> str | None:
        """Return the MEMORY.md index text, or None when nothing is stored."""
        try:
            text = self.index_path.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        return text or None

    def read_memory(self, name: str) -> str | None:
        try:
            return self.memory_path(name).read_text(encoding="utf-8")
        except OSError:
            return None

    def list_memories(self) -> list[str]:
        if not self._dir.is_dir():
            return []
        return sorted(
            p.stem
            for p in self._dir.glob("*.md")
            if p.is_file() and p.name != _INDEX_NAME
        )

    def write_memory(self, name: str, content: str, description: str) -> Path:
        slug = self._validate_slug(name)
        body = content.strip()
        summary = description.strip()
        if not body:
            raise MemoryStoreError("Refusing to store an empty memory.")
        if not summary:
            raise MemoryStoreError("A one-line description is required.")

        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            path = self._dir / f"{slug}.md"
            path.write_text(self._render_memory(slug, summary, body), encoding="utf-8")
        except OSError as exc:
            raise MemoryStoreError(f"Could not write memory {slug!r}: {exc}") from exc

        self._rebuild_index()
        return path

    def delete_memory(self, name: str) -> bool:
        slug = self._validate_slug(name)
        path = self._dir / f"{slug}.md"
        try:
            path.unlink()
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise MemoryStoreError(f"Could not delete memory {slug!r}: {exc}") from exc
        self._rebuild_index()
        return True

    @staticmethod
    def _render_memory(slug: str, description: str, body: str) -> str:
        return f"---\nname: {slug}\ndescription: {description}\n---\n\n{body}\n"

    def _rebuild_index(self) -> None:
        """Regenerate MEMORY.md from the memory files on disk."""
        try:
            entries: list[tuple[str, str]] = []
            for slug in self.list_memories():
                text = self.read_memory(slug) or ""
                entries.append((slug, self._extract_description(text)))

            if not entries:
                self.index_path.unlink(missing_ok=True)
                return

            lines = [f"- [{slug}]({slug}.md) — {desc}" for slug, desc in entries]
            self.index_path.write_text(
                _INDEX_HEADER + "\n" + "\n".join(lines) + "\n", encoding="utf-8"
            )
        except OSError as exc:
            logger.warning("Failed to rebuild memory index: %s", exc)

    @staticmethod
    def _extract_description(text: str) -> str:
        match = _FRONTMATTER_RE.match(text)
        if match:
            for line in match.group(1).splitlines():
                key, _, value = line.partition(":")
                if key.strip() == "description" and value.strip():
                    return value.strip()
        # Fall back to the first non-empty body line.
        body = _FRONTMATTER_RE.sub("", text, count=1)
        for line in body.splitlines():
            if line.strip():
                return line.strip()
        return "(no description)"
