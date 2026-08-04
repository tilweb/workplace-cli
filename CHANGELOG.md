# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Workplace CLI Releases

### [Unreleased]

### [1.1.2] — 2026-08-04

**Mistral-Lean-Agent entfernt (`/leanstall`, `/unleanstall`)**
- Der Upstream-Lean-4-Agent (Modell „leanstral", hartkodiert gegen `api.mistral.ai`) und seine Slash-Commands `/leanstall`/`/unleanstall` (TUI + ACP) sind entfernt — reines Mistral-Feature ohne Adacor-Bezug. Inkl. `lean.md`-Prompt, `SystemPrompt.LEAN`, Skill-Doku. Die generische `install_required`/`installed_agents`-Mechanik bleibt (nicht Mistral-spezifisch).

**Fix: „What's new"-Banner zeigte Upstream-Inhalt**
- `whats_new.md` trug noch den Mistral-Vibe-v2.9.4-Text (`/rename` etc.) und wurde so beim Update angezeigt. Ersetzt durch die echten Workplace-1.1-Highlights (Vision, Datei-Anhang, Mistral raus, notify-only Update).

### [1.1.1] — 2026-08-04

**Datei per Copy & Paste anhängen (Vision Phase 4B)**
- Wird eine Datei ins Eingabefeld eingefügt (das Terminal fügt beim Copy & Paste bzw. Drop ihren Pfad ein), wird sie automatisch als `@`-Mention eingefügt und damit angehängt — sichtbar im Feld. Genau **eine** Datei: Ordner und Mehrfachauswahl werden abgefangen (mit Hinweis); Pfade mit Leerzeichen werden gequotet. Greift über Textuals Paste-Event: Copy & Paste einer Datei funktioniert überall; echtes Drag & Drop nur in Terminals, die Drops als Paste senden (z.B. iTerm2) — **Terminal.app liefert TUI-Drops nicht**.

### [1.1.0] — 2026-08-04

Basiert weiterhin auf Mistral Vibe v2.9.4. Highlights: Vision-Support (Bilder & PDFs), Mistral aus dem Modell-Picker entfernt, Default-Modell `qwen3.5-35b`, notify-only Update-Verhalten, plus mehrere Rebrand-/Prod-Fixes.

**`web_fetch` auf http(s) beschränkt (kein `file://`-Prompt mehr)**
- `web_fetch` lehnte `file://` zwar schon ab, zeigte aber vorher einen verwirrenden „fetching from file:"-Permission-Prompt (weil `_normalize_url` `file:///x` zu `https://file:...` verhunzte). Jetzt: explizite Nicht-http(s)-Schemes werden nicht mehr umgeschrieben, kein Prompt, sofortiger klarer Fehler „Invalid URL scheme". Bare `host:port` (z.B. `example.com:8080`) bekommt weiterhin `https://`. Beschreibung ergänzt: für lokale Dateien `read_file` nutzen.

**Fix: discovered Vision-Modelle wurden nicht als vision-fähig erkannt**
- `supports_vision` war nur am hartkodierten Default gesetzt; ein via `/models`-Discovery geladenes (und im Picker gewähltes) `qwen3-5-a3b-35b-256k` galt als Text-Modell → der Vision-Guard verwarf Bilder/PDFs, das Modell sah nur den Platzhalter. Jetzt markiert eine kuratierte Menge (`VISION_CAPABLE_MODEL_NAMES`: qwen3.5-35b + thinking, pixtral) die Modelle sowohl in `DEFAULT_MODELS` als auch in der Discovery.

**ACP-Bilder von Clients (Vision Phase 4)**
- Der ACP-Agent deklariert jetzt `image=true` und nimmt Bild-Content-Blocks von ACP-Clients (Zed etc.) entgegen: eingehende `ImageContentBlock`s (base64 `data` + `mime_type`) werden zu `image_url`-Parts und an die User-Nachricht gehängt (via `act(images=…)`, inkl. Vision-Guard). Neu: `VibeAcpAgentLoop._build_images`.
- Hinweis: Clipboard-Image-Paste in der TUI ist bewusst zurückgestellt (terminalspezifisch); TUI-Bildinput geht bereits über `@bild.png` (Phase 1).

**PDF/Dokumente lesen (Vision Phase 3)**
- `read_file` auf eine `.pdf`-Datei rendert die Seiten zu Bildern (via `pypdfium2` + `Pillow`, beide permissiv lizenziert — bewusst **nicht** PyMuPDF wegen AGPL) und hängt sie als Vision-Input an. End-to-end gegen Adacor + `qwen3.5-35b` verifiziert (PDF mit Text „BANANE" → korrekt gelesen).
- Cap: erste 10 Seiten (`MAX_PDF_PAGES`), Render-Scale 2×, PDF >25 MB werden übersprungen. Neu: `vibe/core/utils/documents.py`; `ReadFileResult.image_urls` (Liste, für mehrseitige Dokumente). Neue Dependencies: `pypdfium2`, `pillow`.

**Bilder lesen via `read_file` (Vision Phase 2)**
- Der Agent kann Bilddateien jetzt selbst „lesen": `read_file` auf eine `.png/.jpg/.jpeg/.gif/.webp`-Datei liefert das Bild als Vision-Input (statt Text) — es wird als `image_url` an die `role=tool`-Antwortnachricht gehängt. Adacor akzeptiert Bilder in Tool-Rollen (getestet), daher kein Injektions-Umweg nötig. End-to-end gegen Adacor + `qwen3.5-35b` verifiziert (grünes Bild → „Grün").
- Neuer Tool-Hook `BaseTool.get_result_images()`; `ReadFileResult.image_url` (aus der Text-Serialisierung ausgeschlossen, damit kein base64 in den Prompt läuft); Vision-Guard greift auch hier (Text-Modelle bekommen nur den Platzhalter). Bilder >10 MB werden übersprungen.

**Bild-Input / Vision (Phase 1)**
- Der Agent kann jetzt Bilder „sehen": eine per `@bild.png` gementionte Bilddatei (`.png/.jpg/.jpeg/.gif/.webp`) wird als Vision-Input an die User-Nachricht angehängt (base64 `image_url`, OpenAI-Multimodal-Konvention) und vom generischen (Adacor-)Backend entsprechend serialisiert. End-to-end gegen Adacor + `qwen3.5-35b` verifiziert (rotes Testbild → „Rot").
- Nur an vision-fähige Modelle (`ModelConfig.supports_vision`, gesetzt für `qwen3.5-35b`); bei Text-Modellen werden Bilder mit Warn-Log verworfen statt an die API geschickt. Bilder >10 MB werden übersprungen.
- Neu: `vibe/core/utils/images.py`; `LLMMessage.images`; `OpenAIAdapter._images_to_api`; Guard `AgentLoop._images_for_active_model`; Ingestion in `app.py`. (Dokument-/PDF-Lesen und ACP-Bilder folgen in weiteren Phasen.)

**Default-Modell auf `qwen3.5-35b` (Vision-fähig)**
- Default-Modell von `qwen3-30b` (Text) auf `qwen3-5-a3b-35b-256k` (Alias `qwen3.5-35b`) umgestellt. Per curl gegen Adacor verifiziert: das Modell erkennt Bildinhalte korrekt (rotes Testbild → „Rot") und der Endpoint akzeptiert OpenAI-Style `image_url`-Parts — Voraussetzung fuer die kommende Bild-/Dokument-Unterstuetzung (Vision).

**Update: notify-only statt stillem Self-Upgrade**
- `enable_auto_update` Default auf `false`. Der Update-Check beim Start bleibt an und zeigt bei neuer Version einen Hinweis mit Upgrade-Befehl (`brew upgrade workplace-cli` / `uv tool upgrade workplace-cli`) — die App führt aber **kein** ungefragtes `brew/uv upgrade` mehr im Hintergrund aus. Der User startet das Update selbst. (`do_update()` bleibt vorhanden; wer will, kann `enable_auto_update = true` in `config.toml` setzen.)

**Mistral aus dem Modell-Picker entfernt**
- `mistral` ist kein Default-Provider mehr (`DEFAULT_PROVIDERS`), die Mistral-Modelle (`mistral-medium-3.5`, `devstral-small`) sind aus `DEFAULT_MODELS` raus. `/model` zeigt nur noch Adacor (+ discovered) und `llamacpp`/`local`. Mistral-Backend-Code bleibt; wer will, kann Mistral per `config.toml` (`[[providers]]`) wieder hinzufügen.
- Onboarding-Fallback zeigt jetzt auf den Default-Provider (adacor) statt Mistral (behebt zugleich einen `StopIteration`-Crash, da der bisherige Fallback den entfernten Mistral-Default suchte).

**Kritisch: frischer Install crasht durch `mcp 2.0.0`**
- `pyproject.toml` hatte `mcp>=1.14.0` ohne Obergrenze. Ein frischer `uv tool install git+…/workplace-cli` (der README-Weg) zieht `mcp 2.0.0`, wo `streamablehttp_client` umbenannt wurde → `ImportError` beim Start, CLI unbrauchbar. Von der vollen Test-Suite (`test_cli_tui_fresh_install`) aufgedeckt. Gecappt auf `mcp>=1.14.0,<2`.

**Rebrand-Miss: vergessene `.vibe`-Pfade im Code korrigiert**
- `harness_files/_harness_manager.py`: Projekt-Hooks aus `.workplace/hooks.toml` statt `.vibe/hooks.toml` (wurden bisher nie geladen; altes `.vibe/hooks.toml` wäre in trusted folders ausgeführt worden).
- `acp/acp_logger.py`: ACP-Log-Verzeichnis aus `VIBE_HOME` (`~/.workplace-cli/logs/acp`) statt hart `~/.vibe/…` (respektiert jetzt `WORKPLACE_HOME`).
- `acp/acp_agent_loop.py`: `/proxy`-Meldungen verweisen auf `~/.workplace-cli/.env` statt `~/.vibe/.env`.
- `tools/builtins/grep.py`: Default-Ignore-Datei `.workplaceignore` statt `.vibeignore`.

**Home-Verzeichnis: `VIBE_HOME`-Hijack entschärft (Audit #2)**
- `VIBE_HOME`-Env-Var wird nicht mehr honoriert (`_vibe_home.py`): ein Ex-Mistral-Vibe-User mit gesetztem `VIBE_HOME` haette sonst Config + Adacor-Key still ins alte `~/.vibe/`-Verzeichnis geschrieben. Custom-Home nur noch via `WORKPLACE_HOME`; einmaliger stderr-Hinweis beim Start, falls `VIBE_HOME` gesetzt ist. Tests von `VIBE_HOME` auf `WORKPLACE_HOME` umgestellt, Skill-Doku korrigiert.

**Voice & Narrator ausgeblendet (Audit #3)**
- Voice-Mode, Voice-Transcribe und Narrator (Turn-Summary + TTS) sind hartkodiert gegen `api.mistral.ai` (Mistral-SDK-Realtime bzw. Mistral-Chat-Modell). Bis der Adacor-Voice-Pfad steht (Adacor-Whisper vorhanden, TTS noch nicht), werden sie hinter `VOICE_FEATURES_ENABLED=False` (`vibe/cli/feature_flags.py`) vollstaendig deaktiviert und aus der UI ausgeblendet (`/voice`-Command versteckt, `VoiceManager.is_enabled`/`start_recording` und `NarratorManager` inert) — kein Audio-/Turn-Egress an Mistral mehr, auch nicht bei hand-editierter `config.toml`. Reaktivierung per Schalter (setzt Adacor-Clients voraus).

**GitHub Action rebrandet (Audit #4)**
- `action.yml` von „Mistral Vibe"/`MISTRAL_API_KEY`/`vibe -p` auf „Workplace CLI"/`ADACOR_AI_API_KEY`/`workplace -p` umgestellt.

**Update-Check: `workplace --check-update` (P3)**
- Neues Flag `workplace --check-update` prueft synchron gegen die GitHub-Releases von `tilweb/workplace-cli` und beendet sich mit Terminal-Ausgabe (verfuegbar / aktuell / Fehler); umgeht den 24h-Cache, damit der explizite Check immer frisch ist
- Env-Opt-out `WORKPLACE_NO_UPDATE_CHECK=1` schaltet den automatischen Start-Check ab; das explizite Flag laeuft trotzdem
- Wiederverwendung des bestehenden `update_notifier`-Packages statt eigener `update_check.py`: neu `check_for_update_now`, `build_update_gateway`, `update_checks_disabled` in `vibe/cli/update_notifier/update.py`; Flag-Handling in `vibe/cli/entrypoint.py`; Env-Gate in `app.py::_schedule_update_notification`; Builtin-`vibe`-Skill um `--check-update` ergaenzt; Tests in `tests/update_notifier/test_check_for_update_now.py`

**Eigene Provider dokumentiert + Pfad-Korrektur (P2)**
- README-Abschnitt „Eigene Provider / Modelle hinzufuegen": eigene OpenAI-kompatible Endpoints gehen per `config.toml` (`[[providers]]`/`[[models]]`) — kein Source-Fork, kein YAML-Loader noetig (Discovery + TOML decken den User-Value bereits ab; P2-YAML in der Roadmap auf Doku reduziert)
- Faktische Pfad-Korrektur in README: User-Config liegt in `~/.workplace-cli/config.toml` (nicht `~/.config/workplace/`); API-Keys optional in `~/.workplace-cli/.env`

**Dynamische Modell-Auswahl**
- `/model` listet jetzt Provider-gruppiert: Adacor-Modelle werden zur Laufzeit aus `api.adacor.ai/chat/privateai/v1/models` geholt (kein Auth noetig fuer den Endpoint), Embedding-/Transcribe-Modelle werden gefiltert
- Ollama wird auto-detected: wenn `http://localhost:11434/v1/models` antwortet, taucht der Provider mit allen lokal installierten Modellen im Picker auf — ohne Config-Edit
- Cache in `~/.workplace-cli/models-cache.json` (TTL 1h, override via `WORKPLACE_MODEL_CACHE_TTL_SEC`). Discovered Modelle landen NICHT in `config.toml`, nur das ausgewaehlte `active_model`-Alias
- Picker hat Loading-State („⟳ Refreshing models…") waehrend Hintergrund-Refresh; bereits bekannte Modelle bleiben sofort verfuegbar (optimistisches Rendern)
- Fallback: wenn `active_model` aus dem Cache verschwunden ist (z.B. Cache geleert), faellt `VibeConfig.load()` mit Warn-Log auf den Default-Modell-Alias zurueck statt zu crashen
- Files: neu `vibe/core/llm/model_discovery.py`, `tests/test_model_discovery.py`, `tests/test_model_discovery_load_integration.py`, `tests/cli/test_ui_model_picker_dynamic.py`; geaendert `vibe/cli/textual_ui/widgets/model_picker.py`, `vibe/cli/textual_ui/app.py`, `vibe/core/config/_settings.py`, `vibe/core/paths/`

**Bugfixes**
- `app.tcss`: nicht-aufgeloeste CSS-Variable `$mistral_orange` durch `$workplace_purple` ersetzt (`border-remote`-Style)
- Theme-Name `textual-ansi` ist in Textual 8.2.5+ umbenannt zu `ansi-dark` — startete sonst mit `InvalidThemeError`. Neuer Helper `vibe/cli/textual_ui/_theme_compat.py` waehlt zur Laufzeit das passende Theme (8.2.4 ✓ + 8.2.5+ ✓), mit Fallback auf `textual-dark`. Drei Aufruf-Stellen patched: `app.py`, `setup/onboarding/__init__.py`, `setup/trusted_folders/trust_folder_dialog.py`

**Kritisch: Auto-Update auf falsche Quelle**
- Upstream-Code fragte `pypi.org/simple/mistral-vibe` ab und verglich die Mistral-Releases (`2.9.x`) mit unserer eigenen Version (`1.0.0`). Folge: das auto-update zog ein Mistral-Wheel ueber unser installiertes `workplace-cli` und meldete „updated to 2.9.6 — please restart". Fix in `app.py`: `GitHubUpdateGateway(owner="tilweb", repository="workplace-cli")` statt PyPI; in `update.py`: `UPDATE_COMMANDS` referenziert jetzt `workplace-cli`; User-Agent + Banner-/Suspend-Texte gebrandet.

**Branding-Politur**
- Onboarding-Welcome zeigt jetzt „Workplace CLI" statt „Mistral Vibe"
- Setup-complete-Hinweis verweist auf `workplace`-Binary statt `vibe`
- Update-Banner und Suspend-Hinweis sagen „Workplace CLI"
- ACP-Identifikation (`agent_info.name`/`title`) auf `@adacor/workplace-cli` + „Workplace CLI" — ACP-Clients (Zed etc.) sehen jetzt unsere Identitaet
- ACP-Setup-Method id/description/label gebrandet
- `vibe-acp --help` zeigt „Run Workplace CLI in ACP mode"
- OpenTelemetry-Span-Namespace `mistral_vibe` → `workplace_cli` (Service-Name `mistral-vibe` → `workplace-cli`) — relevant fuer alle Otel-Konsumenten
- Onboarding-API-Key-Screen verweist auf `github.com/tilweb/workplace-cli` statt Mistral-Repo
- Self-Awareness-Skill (`vibe`) komplett auf Workplace CLI umgebrandet: alle Pfade (`~/.vibe/` → `~/.workplace-cli/`, `.vibe/` → `.workplace/`), Env-Vars (`VIBE_` → `WORKPLACE_`) und CLI-Beispiele (`vibe …` → `workplace …`) korrigiert. Mistral-Modell-IDs (`mistral-vibe-cli-latest` etc.) bleiben — das sind echte API-Endpoint-Namen.

### [1.0.0] — 2026-05-13

Initialer Workplace-CLI-Release auf Basis Mistral Vibe v2.9.4.

**Adacor-Branding und -Identitaet**
- Paket umbenannt: `mistral-vibe` → `workplace-cli`
- Binary: `vibe` → `workplace` (Legacy-Binary `vibe` bleibt fuer Migration verfuegbar)
- Banner, Spinner-Farben (Mistral-Orange → Workplace-Purple), Persona-Prompts

**Provider/Modelle**
- Adacor AI (`api.adacor.ai/chat/privateai/v1`) als Default-Provider
- Qwen 3 30B (256k) als Default-Modell
- Mistral- und llama.cpp-Provider bleiben fuer User mit eigenem Setup verfuegbar

**Konfiguration**
- Per-Project-Config-Dir: `.vibe/` → `.workplace/`
- User-Home-Config: `~/.vibe/` → `~/.config/workplace/`
- Env-Prefix: `VIBE_` → `WORKPLACE_`

**Datenschutz**
- Telemetrie standardmaessig **deaktiviert** (`enable_telemetry = False`)
- Mistral-Datalake-Endpoint entfernt
- Opt-in: `WORKPLACE_TELEMETRY=local` schreibt JSONL in `~/.config/workplace/usage.jsonl`. `=remote` benoetigt `WORKPLACE_TELEMETRY_URL`.

**Bugfix uebernommen**
- `tool_choice`-Parameter nur senden wenn auch `tools` mitgegeben werden (sonst rejected OpenAI-kompatible Backends wie Adacor den Request)

---

## Upstream (Mistral Vibe) Releases

## [2.9.4] - 2026-05-05

### Added

- `/rename` command to rename the current session
- `feat: vibe.at_mention_inserted` telemetry event
- "Always allow" tool permissions persist across sessions
- Eager agent-loop warmup so `vibe.ready` telemetry fires sooner

### Changed

- `bash` (`!command`) bang commands run via async subprocess for better latency
- Bumped `mistral` SDK to 2.4.4
- Bumped `cryptography` to address upstream CVEs

### Fixed

- Preserve `non_retryable` flag on exceptions raised through `_chat` / `_chat_streaming`, so callers driving the agent loop from a Temporal activity can signal "do not retry"
- `/clear` no longer chains `parent_session_id` to the previous session
- `vibe.new_session` telemetry no longer fires when resuming a session

### Removed

- Windows ARM build artifacts (no longer published; required to bump `cryptography`)


## [2.9.3] - 2026-04-30

### Added

### Changed

### Fixed

- Fix textual version

### Removed


## [2.9.2] - 2026-04-29

### Fixed

- Teleport surfaces the latest GitHub connection status while polling


## [2.9.1] - 2026-04-29

### Added

- Connector OAuth authentication flow in `/mcp` menu
- `ConfigPatch` operation types for Vibe Code
- `extra_headers` field to `ProviderConfig`
- Structured metadata on ACP tool results
- `vibe.user_cancelled_action` ACP telemetry coverage
- `vibe.new_session` telemetry event emitted whenever the session is reset

### Changed

- Migrated default model to `mistral-medium-3.5`


## [2.9.0] - 2026-04-28

### Added

- Scratchpad directory for temporary working files shared with subagents
- `/copy` slash command
- Experimental hooks system with post-agent-turn lifecycle
- OpenAI Responses API adapter
- ACP session fork and session close support
- Thinking level picker in ACP CLI
- `--trust` session-only flag and fail-fast behavior in `-p` mode
- Opus 4.7 model support
- `ConfigLayer` for layered configuration resolution
- `~/.vibe/prompts` overrides for builtin prompts
- Enable/disable MCP servers and individual tools from `/mcp` menu
- Custom compaction instructions via `/compact`
- `vibe.ready` telemetry event
- Usage updates sent after every LLM turn for ACP
- Headless section in system prompt to prevent bad model behavior

### Changed

- Renamed `auto_approve` config to `bypass_tool_permissions`
- Increased feedback bar frequency with cooldown and TOML cache
- Feedback bar only shown when active model is Mistral
- Centralized telemetry metadata construction and wired through entrypoints
- Preserved stable session identity across compact/fork/rewind
- Filtered remote sessions by current user and deduped continue-as-new
- `--continue` now only looks for sessions of the current working directory
- Batched widget mounts and narrowed CSS selectors for UI performance

### Fixed

- Autocomplete popup height calculation for wrapped lines
- Autocomplete popup dismissed on tab completion and escape
- Double Ctrl+C/Ctrl+D required to quit instead of killing session immediately
- Context window overrun now shows a friendly error message
- `MallocStackLogging` error messages suppressed in CLI input
- `index.lock` leftover on interrupted deferred init
- Safe `find` commands allowed by default
- Session ID preserved when resuming sessions through ACP
- Usage updates sent after tool results instead of tool streams in ACP
- KV cache warming via x-affinity in count tokens


## [2.8.1] - 2026-04-21

### Fixed

- Fixed changelog and whats_new


## [2.8.0] - 2026-04-21

### Added

- Builtin skills system with self-awareness skill
- `cwd` configuration parameter for MCP stdio servers
- `/connectors` as alias for `/mcp` and `R` refresh shortcut in MCP browser
- `MergeFieldMetadata` and annotated merge strategy helpers for config schemas
- `vibe.request_sent` telemetry event fired before each LLM API call
- Model alias to `tool_call_finished` telemetry event

### Changed

- Deferred heavy init in subagents and ACP sessions to background thread
- Renamed `request_sent` telemetry fields and added `nb_prompt_chars`
- Sorted connectors in `/mcp` menu by connection state then alphabetically

### Fixed

- `/debug` command no longer throws
- Race condition in banner initialization dropping initial state

### Removed

- `/terminal-setup` command

## [2.7.6] - 2026-04-16

### Added

- `MergeStrategy` enum and merge logic for configuration
- `call_source=vibe_code` field in LLM request metadata
- "Other" task type for non-code requests in CLI prompt

### Changed

- Parallelized git subprocess calls during startup
- Extracted command registry and refactored skill resolution
- 1M context window and thinking budget max for opus
- Updated default telemetry URL to `api.mistral.ai`

### Fixed

- Markdown fence context loss causing streaming rendering problems
- Proxy chain URLs in `api_base` parsing

### Removed

- Alt+Left / Alt+Right key bindings from chat input

## [2.7.5] - 2026-04-14

### Changed

- Display detected files and LLM risks in trust folder dialog
- Text-to-speech via the Mistral SDK with telemetry tracking
- Deferred MCP and git I/O to background thread for faster CLI startup
- Made telemetry URL configurable
- Bumped Textual to 8.2.1

### Fixed

- Encoding detection fallback in `read_safe` for non-UTF-8 files
- Config saving logic cleanup

## [2.7.4] - 2026-04-09

### Added

- Console View for enhanced debugging and monitoring
- `/mcp` command to display MCP servers and their status
- Manual command output forwarding to agent context

### Changed

- Improved web_fetch content truncation for better readability
- Lazily load heavy dependencies to improve startup time
- Optimized folder parsing at startup using scandir
- Include file name in search_replace result display

### Fixed

- Stale configurations from subagent switch
- ValueError on OTEL context detach in agent_span
- Clipboard toast preview replaced with fixed text
- Only agents with type "agent" are loadable with --agent flag
- Made chat_url nullable in ChatAssistantPublicData
- Normalized OTEL span exporter endpoint
- Removed redundant permission prompts for parallel tool calls needing the same permission
- Removed bottom margin issue in UI
- Never crash before ACP server starts
- Use skill in recent commands via the up-arrow navigation
- Fixed loading order issues in vibe initialization

## [2.7.3] - 2026-04-03

### Added

- `/data-retention` slash command to view Mistral AI's data retention notice and privacy settings

## [2.7.2] - 2026-04-01

### Added

- Alt+Left / Alt+Right keyboard shortcuts for word-wise cursor movement in chat input

### Changed

- Refactored narrator into a dedicated narrator manager

### Fixed

- Broken build on Linux
- Errored MCP servers are now excluded from the banner count
- Improved bash denylist matching and error messages
- Command messages are now skipped during rewind navigation

## [2.7.1] - 2026-03-31

### Added

- ACP message-id support for reliable message boundary identification
- Reasoning effort parameter for supported models

### Changed

- Updated MistralAI SDK
- Updated ACP SDK dependency
- Refined system prompt wording and structure
- Reduced scroll sensitivity to 1 line per tick for smoother scrolling

### Fixed

- Non-standard HTTP 529 status codes now handled gracefully in error formatting and retried
- Text selection errors when copying from unmounting components
- Excluded "injected" field from user messages in generic backend

## [2.7.0] - 2026-03-24

### Added

- Rewind mode to navigate and fork conversation history

### Fixed

- Preserve message_id when aggregating streaming LLM chunks
- Improved error handling for SDK response errors

## [2.6.2] - 2026-03-23

### Changed

- Pinned agent-client-protocol dependency back to 0.8.1

### Removed

- Context usage updates via ACP

## [2.6.1] - 2026-03-23

### Changed

- Loosened agent-client-protocol version constraint from pinned to minimum bound

## [2.6.0] - 2026-03-23

### Added

- OTEL tracing support for observability
- Skill tool for managing task lists and workflows
- Text-to-speech (TTS) functionality
- Standalone --resume command for session picker
- BFS for vibe folders to improve startup performance
- List-based model picker for /model command
- is_user_prompt flag to Mistral metadata header
- Correlation ID in user feedback calls
- Current date added to system prompt in vibe-work
- TypeScript type inference for large tool outputs in vibe-work-harness

### Changed

- Updated agent-client-protocol to 0.9.0a1
- Changed inline code color from yellow to green
- Removed "You have no internet access" from CLI prompt
- Fine-grained permission system improvements
- Inject system certs into vibe-acp frozen binary via truststore

### Fixed

- Streaming for currently streamed message when switching agents
- Proper UI updates when tools switch current agents
- Space key functionality when holding shift
- Empty TextChunk not appended when reasoning has no text content
- Messages removed from user feedback event
- Bash allowlist/denylist activation on Windows
- Improved scrolling performance
- ACP error handling in webview
- Context usage updates sent via ACP
- Include `exit_plan_mode` tool only in plan mode

## [2.5.0] - 2026-03-16

### Added

- Dedicated theorem proving agent powered by leanstral, setup with /leanstall
- More advanced AGENTS.md support:
  - AGENTS.md in ~/.vibe/ folder for user-level agent instructions
  - AGENTS.md for subfolders and in parent folders
- Mistral Code API key info displayed in CLI banner
- Voice mode with real-time transcription support
- Parallel tool execution for improved performance
- Structured ACP error classes for better error handling

### Changed

- Bash allowlist/denylist now active on Windows
- Auto-completion relevance improved with better filename and path matching
- History navigation no longer filters by prefix
- Updated to Mistral SDK v2 import structure
- Removed `find` from bash default allowlist to prevent -exec abuse

### Fixed

- Improved scrolling performance
- Web search tool now infers server URL from provider config

## [2.4.2] - 2026-03-12

### Added

- Session ID included in telemetry events for better tracing

### Changed

- Skills now extract arguments when invoked, improving parameter handling
- Auto-compact threshold falls back to global setting when not defined at model level
- Update notification toast no longer times out, ensuring the user sees the restart prompt
- Removed `file_content_before` from Vibe Code, reducing payload size

## [2.4.1] - 2026-03-10

### Added

- `HarnessFilesManager` for selective loading of harness files, enabling SDK usage without accessing the file system.

### Changed

- Web search tool infers server URL from provider config instead of hardcoded production API
- `ask_user_questions` tool disabled in prompt mode

### Fixed

- Space key fix extended to all `Input` widgets (question prompts, proxy setup) in VS Code terminal
- Ruff isort/formatter config conflict resolved (`split-on-trailing-comma` set to `false`)

## [2.4.0] - 2026-03-09

### Added

- User plan displayed in the CLI banner
- Reasoning effort configuration and thinking blocks adapter

### Changed

- Auto-compact threshold is now per-model
- Removed expensive file scan from system prompt; cached git operations for faster agent switching
- Improved plan mode
- Updated `whoami` response handling with new plan type and name fields

### Fixed

- Space key works again in VSCode 1.110+
- Arrow-key history navigation at wrapped-line boundaries in chat input
- UTF-8 encoding enforced when reading metadata files
- Update notifier no longer crashes on unexpected response fields

## [2.3.0] - 2026-02-27

### Added

- /resume command to choose which session to resume
- Web search and web fetch tools for retrieving and searching web content
- MCP sampling support: MCP servers can request LLM completions via the sampling protocol
- MCP server discovery cache (`MCPRegistry`): survives agent switches without re-discovering unchanged servers
- Chat mode for ACP (`session/set_config_options` with `mode=chat`)
- ACP `session/set_config_options` support for switching mode and model
- Tool call streaming: tool call arguments are now streamed incrementally in the UI
- Notification indicator in CLI: terminal bell and window title change on action required or completion
- Subagent traces saved in `agents/` subfolder of parent session directory
- IDE detection in `new_session` telemetry
- Discover agents, tools, and skills in subfolders of trusted directories (monorepo support)
- E2E test infrastructure for CLI TUI

### Changed

- System prompts rewritten for improved model behavior (3-phase Orient/Plan/Execute workflow, brevity rules)
- Tool call display refactored with `ToolCallDisplay`/`ToolResultDisplay` models and per-tool UI customization
- Middleware pipeline replaces observer pattern for system message injections
- Improved permission handling for `write_file`, `read_file`, `search_replace` (allowlist/denylist globs, out-of-cwd detection)
- Proxy setup UI updated with guided bottom-panel wizard
- Smoother color transitions in CLI loader animation
- Dead tool state classes removed (`Grep`, `ReadFile`, `WriteFile` state)

### Fixed

- Agent switch (Shift+Tab) no longer freezes the UI (moved to thread worker)
- Empty assistant messages are no longer displayed
- Tool results returned to LLM in correct order matching tool calls
- Auto-scroll suspended when user has scrolled up; resumes at bottom
- Retry and timeout handling in Mistral backend (backoff strategy, configurable timeout)

### Removed

## [2.2.1] - 2026-02-18

### Added

- Multiple clipboard copy strategies: OSC52 first, then pyperclip fallback when system clipboard is available (e.g. local GUI, SSH without OSC52)
- Ctrl+Z to put Vibe in background

### Changed

- Improve performance around streaming and scrolling
- File watcher is now opt-out by default; opt-in via config
- Bump Textual version in dependencies
- Inline code styling: yellow bold with transparent background for better readability

### Fixed

- Banner: sync skills count after initial app mount (fixes wrong count in some cases)
- Collapsed tool results: strip newlines in truncation to remove extra blank line
- Context token widget: preserve stats listeners across `/clear` so token percentage updates correctly
- Vertex AI: cache credentials to avoid blocking the event loop on every LLM request
- Bash tool: remove `NO_COLOR` from subprocess env to fix snapshot tests and colored output

## [2.2.0] - 2026-02-17

### Added

- Google Vertex AI support
- Telemetry: user interaction and tool usage events sent to datalake (configurable via `enable_telemetry`)
- Skill discovery from `.agents/skills/` (Agent Skills standard) in addition to `.vibe/skills/`
- ACP: `session/load` and `session/list` for loading and listing sessions
- New model behavior prompts (CLI and explore)
- Proxy Wizard (PoC) for CLI and for ACP
- Proxy setup documentation
- Documentation for JetBrains ACP registry

### Changed

- Trusted folders: presence of `.agents` is now considered trustable content
- Logging handling updated
- Pin `cryptography` to >=44.0.0,<=46.0.3; uv sync for cryptography

### Fixed

- Auto scroll when switching to input
- MCP stdio: redirect stderr to logger to avoid unwanted console output
- Align `pyproject.toml` minimum versions with `uv.lock` for pip installs
- Middleware injection: use standalone user messages instead of mutating flushed messages
- Revert cryptography 46.0.5 bump for compatibility
- Pin banner version in UI snapshot tests for stability

## [2.1.0] - 2026-02-11

### Added

- Incremental load of long sessions: windowing (20 messages), "Load more" to fetch older messages, scroll to bottom when resuming
- ACP support for thinking (agent-client-protocol 0.8.0)
- Support for FIFO path for env file

### Changed

- **UI redesign**: new look and layout for the CLI
- Textual UI optimizations: ChatScroll to reduce style recalculations, VerticalGroup for messages, stream layout for streaming blocks, cached DOM queries
- Bumped agent-client-protocol to 0.8.0
- Use UTC date for timestamps
- Clipboard behavior improvements
- Docs updated for GitHub discussions
- Made the Upgrade to Pro banner less prominent

### Fixed

- Fixed inaccurate token count in UI in some cases
- Fixed agent prompt overrides being ignored
- Terminal setup: avoid overwriting Wezterm config

### Removed

- Legacy terminal theme module and agent indicator widget
- Standalone onboarding theme selection screen (replaced by redesign)

## [2.0.2] - 2026-01-30

### Added

- Allow environment variables to be overridden by dotenv files
- Display custom rate limit messages depending on plan type

### Changed

- Made plan offer message more discreet in UI
- Speed up latest session scan and harden validation
- Updated pytest-xdist configuration to schedule single test chunks

### Fixed

- Prevent duplicate messages in persisted sessions
- Fix ACP bash tool to pass full command string for chained commands
- Fix global agent prompt not being loaded correctly
- Do not propose to "resume" when there is nothing to resume

## [2.0.1] - 2026-01-28

### Fixed

- Fix encoding issues in Windows

## [2.0.0] - 2026-01-27

### Added

- Subagent support
- AskUserQuestion tool for interactive user input
- User-defined slash commands through skills
- What's new message display on version update
- Auto-update feature
- Environment variables and timeout support for MCP servers
- Editor shortcut support
- Shift+enter support for VS Code Insiders
- Message ID property for messages
- Client notification of compaction events
- debugpy support for macOS debugging

### Changed

- Mode system refactored to Agents
- Standardized managers
- Improved system prompt
- Updated session storage to separate metadata from messages
- Use shell environment to determine shell in bash tool
- Expanded user input handling
- Bumped agent-client-protocol to 0.7.1
- Refactored UI to require AgentLoop at VibeApp construction
- Updated README with new MCP server config
- Improved readability of the AskUserQuestion tool output

### Fixed

- Use ensure_ascii=False for all JSON dumps
- Delete long-living temporary session files
- Ignore system prompt when saving/loading session messages
- Bash tool timeout handling
- Clipboard: no markup parsing of selected texts
- Canonical imports
- Remove last user message from compaction
- Pause tool timer while awaiting user action

### Removed

- instructions.md support
- workdir setting in config file

## [1.3.5] - 2026-01-12

### Fixed

- bash tool not discovered by vibe-acp

## [1.3.4] - 2026-01-07

### Fixed

- markup in blinking messages
- safety around Bash and AGENTS.md
- explicit permissions to GitHub Actions workflows
- improve render performance in long sessions

## [1.3.3] - 2025-12-26

### Fixed

- Fix config desyncing issues

## [1.3.2] - 2025-12-24

### Added

- User definable reasoning field

### Fixed

- Fix rendering issue with spinner

## [1.3.1] - 2025-12-24

### Fixed

- Fix crash when continuing conversation
- Fix Nix flake to not export python

## [1.3.0] - 2025-12-23

### Added

- agentskills.io support
- Reasoning support
- Native terminal theme support
- Issue templates for bug reports and feature requests
- Auto update zed extension on release creation

### Changed

- Improve ToolUI system with better rendering and organization
- Use pinned actions in CI workflows
- Remove 100k -> 200k tokens config migration

### Fixed

- Fix `-p` mode to auto-approve tool calls
- Fix crash when switching mode
- Fix some cases where clipboard copy didn't work

## [1.2.2] - 2025-12-22

### Fixed

- Remove dead code
- Fix artefacts automatically attached to the release
- Refactor agent post streaming

## [1.2.1] - 2025-12-18

### Fixed

- Improve error message when running in home dir
- Do not show trusted folder workflow in home dir

## [1.2.0] - 2025-12-18

### Added

- Modular mode system
- Trusted folder mechanism for local .vibe directories
- Document public setup for vibe-acp in zed, jetbrains and neovim
- `--version` flag

### Changed

- Improve UI based on feedback
- Remove unnecessary logging and flushing for better performance
- Update textual
- Update nix flake
- Automate binary attachment to GitHub releases

### Fixed

- Prevent segmentation fault on exit by shutting down thread pools
- Fix extra spacing with assistant message

## [1.1.3] - 2025-12-12

### Added

- Add more copy_to_clipboard methods to support all cases
- Add bindings to scroll chat history

### Changed

- Relax config to accept extra inputs
- Remove useless stats from assistant events
- Improve scroll actions while streaming
- Do not check for updates more than once a day
- Use PyPI in update notifier

### Fixed

- Fix tool permission handling for "allow always" option in ACP
- Fix security issue: prevent command injection in GitHub Action prompt handling
- Fix issues with vLLM

## [1.1.2] - 2025-12-11

### Changed

- add `terminal-auth` auth method to ACP agent only if the client supports it
- fix `user-agent` header when using Mistral backend, using SDK hook

## [1.1.1] - 2025-12-10

### Changed

- added `include_commit_signature` in `config.toml` to disable signing commits

## [1.1.0] - 2025-12-10

### Fixed

- fixed crash in some rare instances when copy-pasting

### Changed

- improved context length from 100k to 200k

## [1.0.6] - 2025-12-10

### Fixed

- add missing steps in bump_version script
- move `pytest-xdist` to dev dependencies
- take into account config for bash timeout

### Changed

- improve textual performance
- improve README:
  - improve windows installation instructions
  - update default system prompt reference
  - document MCP tool permission configuration

## [1.0.5] - 2025-12-10

### Fixed

- Fix streaming with OpenAI adapter

## [1.0.4] - 2025-12-09

### Changed

- Rename agent in distribution/zed/extension.toml to mistral-vibe

### Fixed

- Fix icon and description in distribution/zed/extension.toml

### Removed

- Remove .envrc file

## [1.0.3] - 2025-12-09

### Added

- Add LICENCE symlink in distribution/zed for compatibility with zed extension release process

## [1.0.2] - 2025-12-09

### Fixed

- Fix setup flow for vibe-acp builds

## [1.0.1] - 2025-12-09

### Fixed

- Fix update notification

## [1.0.0] - 2025-12-09

### Added

- Initial release
