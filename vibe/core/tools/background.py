"""Background process management for the bash tool.

Long-running commands (dev servers, log tails, watchers, slow builds) can be
started detached so they don't block the agent. Their output is drained into
per-process buffers that later ``bash_output`` calls read incrementally, and
``kill_bash`` terminates them. A single module-level manager holds the state
for the running session.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from vibe.core.logger import logger
from vibe.core.utils.async_subprocess import kill_async_subprocess


@dataclass
class BackgroundProcess:
    shell_id: str
    command: str
    proc: asyncio.subprocess.Process
    stdout_buf: bytearray = field(default_factory=bytearray)
    stderr_buf: bytearray = field(default_factory=bytearray)
    stdout_read: int = 0
    stderr_read: int = 0
    tasks: list[asyncio.Task[None]] = field(default_factory=list)

    @property
    def running(self) -> bool:
        return self.proc.returncode is None

    @property
    def returncode(self) -> int | None:
        return self.proc.returncode


class BackgroundProcessManager:
    """Tracks detached shells started via ``bash(run_in_background=True)``."""

    def __init__(self) -> None:
        self._procs: dict[str, BackgroundProcess] = {}
        self._counter = 0

    def register(
        self, command: str, proc: asyncio.subprocess.Process
    ) -> BackgroundProcess:
        self._counter += 1
        shell_id = f"bash-{self._counter}"
        bp = BackgroundProcess(shell_id=shell_id, command=command, proc=proc)
        bp.tasks = [
            asyncio.create_task(self._drain(proc.stdout, bp.stdout_buf)),
            asyncio.create_task(self._drain(proc.stderr, bp.stderr_buf)),
        ]
        self._procs[shell_id] = bp
        return bp

    @staticmethod
    async def _drain(stream: asyncio.StreamReader | None, buf: bytearray) -> None:
        if stream is None:
            return
        try:
            while True:
                chunk = await stream.read(4096)
                if not chunk:
                    break
                buf.extend(chunk)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Background output reader stopped: %s", exc)

    def get(self, shell_id: str) -> BackgroundProcess | None:
        return self._procs.get(shell_id)

    def list(self) -> list[BackgroundProcess]:
        return list(self._procs.values())

    @staticmethod
    def read_new(bp: BackgroundProcess) -> tuple[str, str]:
        """Return stdout/stderr appended since the previous read."""
        out = bytes(bp.stdout_buf[bp.stdout_read :])
        err = bytes(bp.stderr_buf[bp.stderr_read :])
        bp.stdout_read = len(bp.stdout_buf)
        bp.stderr_read = len(bp.stderr_buf)
        return (
            out.decode("utf-8", errors="replace"),
            err.decode("utf-8", errors="replace"),
        )

    async def kill(self, shell_id: str) -> bool:
        bp = self._procs.get(shell_id)
        if bp is None:
            return False
        if bp.running:
            await kill_async_subprocess(bp.proc, kill_process_group=True)
        for task in bp.tasks:
            task.cancel()
        return True


_manager = BackgroundProcessManager()


def get_background_manager() -> BackgroundProcessManager:
    return _manager
