from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path

from vibe import VIBE_ROOT


class GlobalPath:
    def __init__(self, resolver: Callable[[], Path]) -> None:
        self._resolver = resolver

    @property
    def path(self) -> Path:
        return self._resolver()


_DEFAULT_VIBE_HOME = Path.home() / ".workplace-cli"


def _get_vibe_home() -> Path:
    # === ADACOR PATCH: nur WORKPLACE_HOME honorieren ===
    # Der Upstream-`VIBE_HOME`-Env-Fallback wird bewusst NICHT gelesen: Ein
    # Ex-Mistral-Vibe-User hat evtl. noch `VIBE_HOME` (z.B. auf ~/.vibe)
    # gesetzt. Würde Workplace CLI das still übernehmen, landeten Config und
    # Adacor-Key im falschen (Mistral-Ära-)Verzeichnis, während alle Meldungen
    # ~/.workplace-cli/ anzeigen. Custom-Home nur noch via WORKPLACE_HOME.
    if workplace_home := os.getenv("WORKPLACE_HOME"):
        return Path(workplace_home).expanduser().resolve()
    return _DEFAULT_VIBE_HOME
    # === ADACOR PATCH END ===


VIBE_HOME = GlobalPath(_get_vibe_home)
GLOBAL_ENV_FILE = GlobalPath(lambda: VIBE_HOME.path / ".env")
SESSION_LOG_DIR = GlobalPath(lambda: VIBE_HOME.path / "logs" / "session")
TRUSTED_FOLDERS_FILE = GlobalPath(lambda: VIBE_HOME.path / "trusted_folders.toml")
LOG_DIR = GlobalPath(lambda: VIBE_HOME.path / "logs")
LOG_FILE = GlobalPath(lambda: VIBE_HOME.path / "logs" / "vibe.log")
CACHE_FILE = GlobalPath(lambda: VIBE_HOME.path / "cache.toml")
HISTORY_FILE = GlobalPath(lambda: VIBE_HOME.path / "vibehistory")
PLANS_DIR = GlobalPath(lambda: VIBE_HOME.path / "plans")
# === ADACOR PATCH START: dynamic model discovery cache ===
MODELS_CACHE_FILE = GlobalPath(lambda: VIBE_HOME.path / "models-cache.json")
# === ADACOR PATCH END ===

DEFAULT_TOOL_DIR = GlobalPath(lambda: VIBE_ROOT / "core" / "tools" / "builtins")
