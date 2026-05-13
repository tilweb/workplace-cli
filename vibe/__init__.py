from __future__ import annotations

from pathlib import Path

VIBE_ROOT = Path(__file__).parent

# === ADACOR PATCH START: version metadata ===
# Workplace-CLI ist ein Fork von Mistral Vibe. Unsere Versionierung ist
# unabhaengig vom Upstream; das Upstream-Tag bleibt fuer Nachvollziehbarkeit
# in `__upstream_version__` erhalten und wird im `--version`-Output gezeigt.
__version__ = "1.0.0"
__upstream_version__ = "2.9.4"
# === ADACOR PATCH END ===
