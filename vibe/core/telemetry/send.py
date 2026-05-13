"""
Telemetry Client — Workplace CLI Fork

=== ADACOR PATCH: kompletter Rewrite ===

Upstream sendet Events an `https://api.mistral.ai/v1/datalake/events`. Fuer
Workplace-CLI als internes Adacor-Tool ist das ein Datenschutz-Problem:
Session-IDs, Tool-Aufrufe und Modell-Wahl wuerden an Mistral fliessen — auch
wenn der User Adacor-Modelle nutzt (sobald jemand zwischendurch zum
Mistral-Provider wechselt und einen Key gesetzt hat).

Stattdessen:
- **Default off** (`VibeConfig.enable_telemetry = False`)
- Opt-in via `WORKPLACE_TELEMETRY` env var:
  - `WORKPLACE_TELEMETRY=off` (default): nichts senden, nichts schreiben
  - `WORKPLACE_TELEMETRY=local`: JSONL-Append in `~/.config/workplace/usage.jsonl`
  - `WORKPLACE_TELEMETRY=remote`: HTTP-POST an `WORKPLACE_TELEMETRY_URL` (Phase 4)

Keine Events werden an `api.mistral.ai` gesendet — auch nicht wenn der User
Mistral-Provider aktiv hat. Die alten `_get_mistral_*`-Helper sind entfernt.

Die oeffentliche API (`TelemetryClient`-Klasse + Methoden) bleibt
signatur-kompatibel mit Upstream, damit Aufrufstellen im Agent-Loop nicht
angefasst werden muessen.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import httpx

from vibe import __version__
from vibe.core.config import VibeConfig
from vibe.core.llm.format import ResolvedToolCall
from vibe.core.telemetry.build_metadata import build_base_metadata
from vibe.core.telemetry.types import (
    AgentEntrypoint,
    EntrypointMetadata,
    TelemetryCallType,
)

if TYPE_CHECKING:
    from vibe.core.agent_loop import ToolDecision


def _get_mode() -> Literal["off", "local", "remote"]:
    raw = os.environ.get("WORKPLACE_TELEMETRY", "off").strip().lower()
    if raw in ("local", "remote"):
        return raw  # type: ignore[return-value]
    return "off"


def _local_telemetry_file() -> Path:
    """Resolve the local telemetry file (lazy — User-Home expansion).

    Default: ~/.config/workplace/usage.jsonl. Override via WORKPLACE_TELEMETRY_FILE.
    """
    override = os.environ.get("WORKPLACE_TELEMETRY_FILE")
    if override:
        return Path(override).expanduser()
    return Path("~/.config/workplace/usage.jsonl").expanduser()


def _remote_url() -> str | None:
    url = os.environ.get("WORKPLACE_TELEMETRY_URL", "").strip()
    return url or None


class TelemetryClient:
    """API-kompatible Telemetry-Klasse, ohne Mistral-Anbindung."""

    def __init__(
        self,
        config_getter: Callable[[], VibeConfig],
        session_id_getter: Callable[[], str | None] | None = None,
        parent_session_id_getter: Callable[[], str | None] | None = None,
        entrypoint_metadata_getter: Callable[[], EntrypointMetadata | None]
        | None = None,
    ) -> None:
        self._config_getter = config_getter
        self._session_id_getter = session_id_getter
        self._parent_session_id_getter = parent_session_id_getter
        self._entrypoint_metadata_getter = entrypoint_metadata_getter
        self._client: httpx.AsyncClient | None = None
        self._pending_tasks: set[asyncio.Task[Any]] = set()
        self.last_correlation_id: str | None = None

    def _is_enabled(self) -> bool:
        """User-Config + Env-Var beide aktiv?"""
        try:
            if not self._config_getter().enable_telemetry:
                return False
        except ValueError:
            return False
        return _get_mode() != "off"

    def is_active(self) -> bool:
        return self._is_enabled()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(5.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self._client

    @property
    def session_id(self) -> str | None:
        if self._session_id_getter is None:
            return None
        return self._session_id_getter()

    @property
    def parent_session_id(self) -> str | None:
        if self._parent_session_id_getter is None:
            return None
        return self._parent_session_id_getter()

    def build_client_event_metadata(self) -> dict[str, str]:
        return build_base_metadata(
            entrypoint_metadata=(
                self._entrypoint_metadata_getter()
                if self._entrypoint_metadata_getter is not None
                else None
            ),
            session_id=self.session_id,
            parent_session_id=self.parent_session_id,
        )

    def _write_local(self, event_name: str, properties: dict[str, Any]) -> None:
        """Append JSONL-Event in lokale Datei. Fire-and-forget, Fehler werden
        verschluckt (Telemetrie darf nie den eigentlichen CLI-Lauf brechen)."""
        try:
            path = _local_telemetry_file()
            path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(
                {"event": event_name, "properties": properties},
                ensure_ascii=False,
                default=str,
            )
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except Exception:
            pass

    def send_telemetry_event(
        self,
        event_name: str,
        properties: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> None:
        if not self._is_enabled():
            return

        properties = self.build_client_event_metadata() | properties
        if correlation_id:
            properties = properties | {"correlation_id": correlation_id}

        mode = _get_mode()
        if mode == "local":
            self._write_local(event_name, properties)
            return

        # mode == "remote"
        url = _remote_url()
        if not url:
            return

        payload = {"event": event_name, "properties": properties}

        async def _send() -> None:
            try:
                await self.client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
            except Exception:
                pass

        task = asyncio.create_task(_send())
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    async def aclose(self) -> None:
        if self._pending_tasks:
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _calculate_file_metrics(
        self,
        tool_call: ResolvedToolCall,
        status: Literal["success", "failure", "skipped"],
        result: dict[str, Any] | None = None,
    ) -> tuple[int, int]:
        nb_files_created = 0
        nb_files_modified = 0
        if status == "success" and result is not None:
            if tool_call.tool_name == "write_file":
                file_existed = result.get("file_existed", False)
                if file_existed:
                    nb_files_modified = 1
                else:
                    nb_files_created = 1
            elif tool_call.tool_name == "search_replace":
                nb_files_modified = 1 if result.get("blocks_applied", 0) > 0 else 0
        return nb_files_created, nb_files_modified

    def send_tool_call_finished(
        self,
        *,
        tool_call: ResolvedToolCall,
        status: Literal["success", "failure", "skipped"],
        decision: ToolDecision | None,
        agent_profile_name: str,
        model: str,
        result: dict[str, Any] | None = None,
        message_id: str | None = None,
    ) -> None:
        verdict_value = decision.verdict.value if decision else None
        approval_type_value = decision.approval_type.value if decision else None

        nb_files_created, nb_files_modified = self._calculate_file_metrics(
            tool_call, status, result
        )

        payload = {
            "tool_name": tool_call.tool_name,
            "status": status,
            "decision": verdict_value,
            "approval_type": approval_type_value,
            "agent_profile_name": agent_profile_name,
            "model": model,
            "nb_files_created": nb_files_created,
            "nb_files_modified": nb_files_modified,
            "message_id": message_id,
        }
        self.send_telemetry_event("workplace.tool_call_finished", payload)

    def send_user_copied_text(self, text: str) -> None:
        payload = {"text_length": len(text)}
        self.send_telemetry_event("workplace.user_copied_text", payload)

    def send_user_cancelled_action(self, action: str) -> None:
        payload = {"action": action}
        self.send_telemetry_event("workplace.user_cancelled_action", payload)

    def send_auto_compact_triggered(
        self,
        *,
        nb_context_tokens_before: int,
        nb_context_tokens_after: int,
        auto_compact_threshold: int,
        status: Literal["success", "failure", "cancelled"],
        session_id: str | None = None,
        parent_session_id: str | None = None,
    ) -> None:
        payload = {
            "nb_context_tokens_before": nb_context_tokens_before,
            "nb_context_tokens_after": nb_context_tokens_after,
            "auto_compact_threshold": auto_compact_threshold,
            "status": status,
        }
        if session_id is not None:
            payload["session_id"] = session_id
            payload["parent_session_id"] = parent_session_id
        self.send_telemetry_event("workplace.auto_compact_triggered", payload)

    def send_slash_command_used(
        self, command: str, command_type: Literal["builtin", "skill"]
    ) -> None:
        payload = {"command": command.lstrip("/"), "command_type": command_type}
        self.send_telemetry_event("workplace.slash_command_used", payload)

    def send_new_session(
        self,
        has_agents_md: bool,
        nb_skills: int,
        nb_mcp_servers: int,
        nb_models: int,
        entrypoint: AgentEntrypoint,
        client_name: str | None,
        client_version: str | None,
        terminal_emulator: str | None = None,
    ) -> None:
        payload = {
            "has_agents_md": has_agents_md,
            "nb_skills": nb_skills,
            "nb_mcp_servers": nb_mcp_servers,
            "nb_models": nb_models,
            "entrypoint": entrypoint,
            "version": __version__,
            "client_name": client_name,
            "client_version": client_version,
            "terminal_emulator": terminal_emulator,
        }
        self.send_telemetry_event("workplace.new_session", payload)

    def send_onboarding_api_key_added(self) -> None:
        self.send_telemetry_event(
            "workplace.onboarding_api_key_added", {"version": __version__}
        )

    def send_request_sent(
        self,
        *,
        model: str,
        nb_context_chars: int,
        nb_context_messages: int,
        nb_prompt_chars: int,
        call_type: TelemetryCallType,
        message_id: str | None = None,
    ) -> None:
        payload = {
            "model": model,
            "nb_context_chars": nb_context_chars,
            "nb_context_messages": nb_context_messages,
            "nb_prompt_chars": nb_prompt_chars,
            "call_source": "workplace_cli",
            "call_type": call_type,
            "message_id": message_id,
        }
        self.send_telemetry_event("workplace.request_sent", payload)

    def send_ready(self, *, init_duration_ms: int) -> None:
        payload = {"init_duration_ms": init_duration_ms}
        self.send_telemetry_event("workplace.ready", payload)

    def send_at_mention_inserted(
        self,
        *,
        nb_mentions: int,
        context_types: dict[str, int],
        file_extensions: dict[str, int] | None,
        message_id: str | None,
    ) -> None:
        payload: dict[str, Any] = {
            "nb_mentions": nb_mentions,
            "context_types": context_types,
            "file_extensions": file_extensions,
            "message_id": message_id,
        }
        self.send_telemetry_event("workplace.at_mention_inserted", payload)

    def send_user_rating_feedback(self, rating: int, model: str) -> None:
        self.send_telemetry_event(
            "workplace.user_rating_feedback",
            {"rating": rating, "version": __version__, "model": model},
            correlation_id=self.last_correlation_id,
        )
