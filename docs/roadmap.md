# Workplace CLI — Roadmap & offene Punkte

Stand: 2026-05-15. Phase 1 (P1) ist abgeschlossen — Repo, Release `v1.0.0`, Homebrew-Tap und CI sind live. Dieses Dokument hält fest:

1. **Persönliche TODOs** für Andreas (lokale Setup-Schritte)
2. **Phasen P2-P5** als detaillierte Folgeschritte mit Begründung, Files, Tests und Aufwand

---

## 1. Persönliches TODO: Xcode Command Line Tools updaten

Bei lokalem `brew install workplace-cli` kam diese Meldung:

```
Error: Your Command Line Tools are too outdated.
Update them from Software Update in System Settings.
You should download the Command Line Tools for Xcode 26.3.
```

Die **Xcode Command Line Tools (CLT)** liefern `clang`, `git`, Headers, libc-Definitionen — Brew braucht das für Bottle-Installs und Linkage-Fixing. Auf der GitHub-Action-macOS-VM ist die aktuelle Version drauf, dort läuft alles grün. Lokal nicht.

### So updatest du

**Option 1 — Software Update** (empfohlen):
1. Apple-Menü → Systemeinstellungen → Allgemein → Softwareupdate
2. „Command Line Tools for Xcode" sollte angeboten werden → installieren

**Option 2 — Falls Software Update nichts anzeigt**:
```sh
sudo rm -rf /Library/Developer/CommandLineTools
sudo xcode-select --install
```
Öffnet einen Dialog, „Installieren" klicken, läuft ~5-10 min.

**Option 3 — Manuell** als DMG: [developer.apple.com/download/all](https://developer.apple.com/download/all/) → „Command Line Tools for Xcode 26.3" runterladen.

### Verifizieren

```sh
xcode-select -p           # /Library/Developer/CommandLineTools
clang --version           # Apple clang version 17.x
brew config | grep CLT    # CLT: <Version>
```

### Anschließend Workplace-CLI testen

```sh
brew untap tilweb/tap 2>/dev/null || true
brew tap tilweb/tap
brew install workplace-cli
workplace --version       # → "workplace 1.0.0"
```

Wenn der Warning `Failed to fix install linkage … rpds.cpython-312-darwin.so` (oder ähnlich für `watchfiles`) erscheint: **ignorieren**, der Install ist trotzdem komplett. Hintergrund: Python-Sub-Deps mit Rust-Extensions haben zu schmale Mach-O-Header für Brew's absolute @rpath-ReWrites. Alles bleibt im venv self-konsistent, das Binary funktioniert.

---

## 2. P2 — Provider/Model-Config aus Source raus in `~/.config/workplace/providers.yaml`

### Ziel

Provider/Modell-Definitionen aus `vibe/core/config/_settings.py` als YAML-Config ausgliedern, sodass User eigene Provider (Ollama, LM Studio, eigene Endpoints) hinzufügen können **ohne Source-Code anzufassen**. Reduziert Konflikt-Surface bei Upstream-Merges drastisch.

### Begründung

Heute leben Adacor- und Mistral-Provider als hartcodiertes `DEFAULT_PROVIDERS = [...]` direkt im Code. Jeder Upstream-Sync, der diese Stelle anfasst, gibt Konflikte. Außerdem: User wollen lokale Modelle (Ollama @ `localhost:11434`, LM Studio @ `localhost:1234`) ergänzen — heute braucht es einen Code-Fork.

### Konkrete Umsetzung

**Neue Datei** `vibe/core/config/_provider_config_loader.py`:

```python
# Liest Provider/Model-Bundles aus folgender Hierarchie (höchste Prio zuerst):
# 1. WORKPLACE_PROVIDERS_CONFIG (env var, Pfad zu YAML)
# 2. ~/.config/workplace/providers.yaml (User-Override)
# 3. /etc/workplace/providers.yaml (System-Default, optional)
# 4. Eingebettete Defaults aus pkg_resources: vibe/core/config/data/default-providers.yaml
#
# User-Config wird gemerged: Provider/Modelle, die nur im User-File stehen,
# werden ergaenzt. Builtin-Provider koennen NICHT ueberschrieben werden (sonst
# koennte ein User versehentlich Adacor-Defaults brechen).
```

**Neue Daten-Datei** `vibe/core/config/data/default-providers.yaml`:

```yaml
providers:
  - name: adacor
    api_base: https://api.adacor.ai/chat/privateai/v1
    api_key_env_var: ADACOR_AI_API_KEY
    backend: generic
    builtin: true

  - name: ollama
    api_base: http://localhost:11434/v1
    api_key_env_var: ""
    backend: generic
    builtin: true

  - name: lmstudio
    api_base: http://localhost:1234/v1
    api_key_env_var: ""
    backend: generic
    builtin: true

  - name: mistral
    api_base: https://api.mistral.ai/v1
    api_key_env_var: MISTRAL_API_KEY
    backend: mistral
    builtin: true

models:
  # Erstes Modell wird DEFAULT_ACTIVE_MODEL.
  - name: qwen3-a3b-30b-256k
    provider: adacor
    alias: qwen3-30b
    builtin: true

  - name: qwen2.5-coder:14b
    provider: ollama
    alias: qwen-local-14b
    builtin: true

  - name: llama3.1:70b
    provider: ollama
    alias: llama-local-70b
    builtin: true

  - name: qwen2.5-coder-32b-instruct
    provider: lmstudio
    alias: lmstudio-coder
    builtin: true

  - name: mistral-vibe-cli-latest
    provider: mistral
    alias: mistral-medium-3.5
    builtin: true
```

**Beispiel User-Config** `~/.config/workplace/providers.yaml`:

```yaml
providers:
  - name: my-internal-llm
    api_base: https://llm.internal.adacor.de/v1
    api_key_env_var: ADACOR_INTERNAL_KEY
    backend: generic

models:
  - name: internal-coder-7b
    provider: my-internal-llm
    alias: internal
```

### Files

- **Neu**: `vibe/core/config/_provider_config_loader.py` (Loader-Logik, ~120 Zeilen)
- **Neu**: `vibe/core/config/data/default-providers.yaml`
- **Geändert**: `vibe/core/config/_settings.py` — `DEFAULT_PROVIDERS` + `DEFAULT_MODELS` werden vom Loader gefüllt statt hartcodiert
- **Geändert**: `pyproject.toml` — `[tool.setuptools.package-data]` ergänzen für `data/*.yaml`
- **Geändert**: `README.md` + `CHANGELOG.md` — User-Config dokumentieren

### Verifikation

| Test | Erwartet |
|---|---|
| `workplace --version` ohne User-Config | Default-Modell `qwen3-30b` |
| User legt `~/.config/workplace/providers.yaml` mit neuem Modell an | `/agent` zeigt das neue Modell zur Auswahl |
| Ollama lokal laufend, `ADACOR_AI_API_KEY` nicht gesetzt | `workplace --agent ollama/qwen-local-14b` funktioniert |
| User versucht `adacor`-Provider zu überschreiben | Loader ignoriert User-Override mit Warnung |

### Aufwand

~3-4h. Loader-Code, YAML-Schema, Tests, Doku.

### Risiken

- **Mistral kann in Upstream-Updates `DEFAULT_PROVIDERS` umstrukturieren** — wir müssen den Loader anpassen falls die Provider-Datenstruktur ändert. Patch-Marker im Settings-File hilft, das schnell zu sehen.
- **Backwards-Compat**: Existierende User-Configs aus alter Vibe-Welt (`~/.vibe/config.toml`) — Migration-Hint im first-run.

---

## 3. P3 — Update-Check + `workplace --check-update`

> **Status (2026-07-01): umgesetzt.** Der automatische Check beim TUI-Start existierte
> bereits (`app.py::_check_update`, GitHub-Releases von `tilweb/workplace-cli`, 24h-Cache,
> `do_update()` mit brew/uv). Ergänzt: explizites **`workplace --check-update`** (synchron,
> Terminal-Output verfügbar/aktuell/Fehler, ignoriert den Cache) und Env-Opt-out
> **`WORKPLACE_NO_UPDATE_CHECK`** für den automatischen Check. Neue Bausteine:
> `check_for_update_now`, `build_update_gateway`, `update_checks_disabled` in
> `vibe/cli/update_notifier/update.py`; Flag-Handling in `entrypoint.py`; Tests in
> `tests/update_notifier/test_check_for_update_now.py`. Abweichung vom Plan unten: keine
> separate `update_check.py`/`last-update-check.json` — das vorhandene `update_notifier`-
> Package (cache.toml) wird wiederverwendet statt dupliziert.

### Ziel

CLI prüft beim Start (oder explizit per `workplace --check-update`), ob es eine neuere Version gibt, und informiert den User mit Install-Befehl.

### Begründung

Workplace-CLI wird intern verteilt — User installieren einmal, vergessen es, laufen jahrelang auf einer alten Version. Ein dezentes Update-Hint beim Start (z.B. einmal pro Tag) bringt Updates schneller ins Team.

### Konkrete Umsetzung

**Neue Datei** `vibe/core/update_check.py`:

```python
# Logik:
# 1. Lese ~/.config/workplace/last-update-check.json (Timestamp + remote_version)
# 2. Wenn last_check < 24h alt → nichts tun
# 3. Sonst: HTTP GET https://api.github.com/repos/tilweb/workplace-cli/releases/latest
#    (5s Timeout, fire-and-forget, kein Fail-bei-Network-Error)
# 4. Wenn remote_version > __version__: schreibe Hint-Banner
# 5. Schreibe last-update-check.json mit jetzt + remote_version
#
# Opt-out: WORKPLACE_NO_UPDATE_CHECK=1
```

**Banner-Format**:

```
─── Update verfügbar ─────────────────────────────────
  Workplace CLI 1.2.0 ist seit 2026-08-15 verfügbar.
  Du nutzt 1.1.3.

  Update:
    brew upgrade workplace-cli
    # oder
    uv tool upgrade workplace-cli

  Changelog: https://github.com/tilweb/workplace-cli/releases/tag/v1.2.0
──────────────────────────────────────────────────────
```

**Trigger-Punkte**:
- **Beim TUI-Start** (`vibe/cli/entrypoint.py`): async im Hintergrund, Banner erscheint erst nach erfolgreichem Check
- **Explizit**: `workplace --check-update` (sync, immer)

### Files

- **Neu**: `vibe/core/update_check.py` (~80 Zeilen)
- **Geändert**: `vibe/cli/entrypoint.py` — async Update-Check-Task starten
- **Geändert**: `argparse`-Setup für `--check-update`-Flag
- **Geändert**: README — Opt-out via `WORKPLACE_NO_UPDATE_CHECK` dokumentieren

### Verifikation

| Test | Erwartet |
|---|---|
| Frisch installiert, ohne Internet | Kein Fehler, kein Banner, kein Crash |
| Mit `WORKPLACE_NO_UPDATE_CHECK=1` | Kein HTTP-Request |
| `last-update-check.json` <24h alt | Kein Request |
| Mock-API gibt Version 99.0.0 | Banner erscheint |
| Mock-API gibt aktuelle Version | Kein Banner |

### Aufwand

~2h. Code + httpx-Mock-Tests.

### Risiken

- **GitHub-API-Rate-Limits** (60 req/h anonym, 5000 mit Token) — bei 24h-Cache pro User unkritisch
- **Privacy**: GitHub sieht den Request (kein User-Identifier, aber IP). Mit Repo-public eh kein Issue
- **Pre-1.0-Versionen**: Semver-Comparison muss `1.2.0-rc1`-Tags ignorieren

---

## 4. P4 — SSO via Adacor-OIDC, `workplace login`

### Ziel

User authentifiziert sich per `workplace login` einmalig via Browser-Flow gegen Adacor-Identity, Token wird in `~/.config/workplace/credentials.json` gespeichert. Kein Copy-Paste-API-Keys mehr.

### Begründung

API-Keys-per-User skaliert nicht: Onboarding eines neuen Adacor-Mitarbeiters bedeutet Key generieren, sicher übermitteln, in Env-Var setzen. Bei Offboarding muss Key revoked werden. SSO via Adacor-OIDC + Token-Refresh ist Standard-Praxis und ohne SSO ist Workplace nicht wirklich enterprise-tauglich.

### Konkrete Umsetzung

**Voraussetzung**: Adacor-Identity-OIDC-Endpoint mit Device-Code-Flow oder PKCE-Flow. Wenn nicht vorhanden, muss DevOps das vorab einrichten.

**Flow**:

1. User: `workplace login`
2. CLI: HTTP-POST an Adacor-OIDC `https://identity.adacor.de/oauth2/device` → bekommt `device_code`, `user_code`, `verification_uri`
3. CLI zeigt User-Code + öffnet Browser zur Verification-URL (per `open` / `xdg-open`)
4. CLI pollt `/token` alle 5s mit dem `device_code` (max 5min)
5. Bei Erfolg: Access-Token + Refresh-Token landen in `~/.config/workplace/credentials.json` (chmod 0600)
6. Token-Refresh transparent vor jedem Adacor-API-Call

**Neue Files**:
- `vibe/core/auth/__init__.py` — Token-Cache, Refresh-Logik
- `vibe/core/auth/oidc.py` — Device-Code-Flow-Implementation
- `vibe/cli/commands/login.py` + `logout.py`

**Geänderte Files**:
- `vibe/core/llm/backend/generic.py` — wenn `provider == "adacor"` und kein API-Key gesetzt: aus Credentials-File lesen, Refresh wenn abgelaufen
- `pyproject.toml` — neue Dep `authlib` oder `requests-oauthlib`

### Files (Übersicht)

- **Neu**: `vibe/core/auth/__init__.py`, `vibe/core/auth/oidc.py` (~250 Zeilen)
- **Neu**: `vibe/cli/commands/login.py`, `vibe/cli/commands/logout.py`
- **Geändert**: `vibe/core/llm/backend/generic.py` — Auth-Header-Injection
- **Geändert**: `pyproject.toml` — `authlib` ergänzen
- **Geändert**: README — `workplace login`-Flow dokumentieren, API-Key als legacy markieren (noch unterstützt, aber discouraged)

### Verifikation

| Test | Erwartet |
|---|---|
| `workplace login` ohne Internet | Klarer Fehler, kein Crash |
| `workplace login` → Browser öffnet → User-Code wird angezeigt | UX ok |
| Nach Login: `workplace` startet ohne ENV-Var | Adacor-Provider funktioniert |
| Token abgelaufen → CLI refresh transparent | Kein User-Hinweis nötig |
| `workplace logout` | Credentials-File gelöscht |
| `ADACOR_AI_API_KEY` ENV-Var gesetzt UND Login vorhanden | ENV gewinnt (Override) |

### Aufwand

~6-8h, inklusive OIDC-Library-Integration und ausgiebigem Token-Refresh-Test. **Plus DevOps-Vorarbeit** für Adacor-Identity-Client-Registrierung.

### Risiken

- **Adacor-Identity nicht bereit** — dann erstmal Mock-Endpoint oder Keycloak-Dev-Instance
- **Token-Storage auf Disk** — `~/.config/workplace/credentials.json` chmod 0600, plus macOS-Keychain als Optional-Backend in einer späteren Iteration
- **Refresh-Race-Conditions** bei parallelen `workplace`-Sessions — Lock-File-Mechanismus oder atomares Read-Refresh-Write

---

## 5. P5 — Auto-Sync mit Upstream (GitHub-Action)

### Ziel

Wöchentlich automatisch prüfen, ob Mistral ein neues Vibe-Release hat. Wenn ja: PR auf `main` mit dem Upstream-Merge erstellen. Bei Konflikten in unseren Adacor-Patch-Files: PR markiert „needs review", sonst auto-mergeable.

### Begründung

Manuell wöchentlich Upstream prüfen vergisst sich. GitHub-Action automatisiert die mechanische Arbeit; Maintainer sieht nur noch echte Konflikte.

### Konkrete Umsetzung

**Neue Datei** `.github/workflows/upstream-sync.yml`:

```yaml
name: Upstream Sync

on:
  schedule:
    - cron: "0 6 * * 1"  # Montags 06:00 UTC
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0
      - name: Add upstream remote
        run: |
          git remote add upstream https://github.com/mistralai/mistral-vibe.git
          git config remote.upstream.tagOpt --no-tags
          git fetch upstream main
      - name: Determine latest upstream tag
        id: upstream
        run: |
          # Hole alle upstream-Tags, finde die hoechste vX.Y.Z
          git fetch upstream "refs/tags/*:refs/tags/upstream-*"
          LATEST=$(git tag --list "upstream-v*" --sort=-v:refname | head -1)
          echo "tag=$LATEST" >> "$GITHUB_OUTPUT"
      - name: Compare with our upstream pointer
        id: needs_sync
        run: |
          OURS=$(git tag --list "upstream/v*" --sort=-v:refname | head -1 || echo "upstream/v0.0.0")
          LATEST="${{ steps.upstream.outputs.tag }}"
          # ... Versions-Vergleich
          echo "should_sync=true" >> "$GITHUB_OUTPUT"
      - name: Create sync branch + merge
        if: steps.needs_sync.outputs.should_sync == 'true'
        run: |
          BRANCH="sync/upstream-${{ steps.upstream.outputs.tag }}"
          git checkout -b "$BRANCH"
          # Merge mit fallback-Strategie
          git merge "${{ steps.upstream.outputs.tag }}" --no-ff --no-edit || true
          # Erkennen ob Konflikte in Patch-Markern stecken
          CONFLICT_IN_PATCHES=$(git diff --name-only --diff-filter=U | xargs -I {} grep -l "ADACOR PATCH" {} 2>/dev/null | wc -l)
          if [ "$CONFLICT_IN_PATCHES" -gt 0 ]; then
            LABEL="needs-review-conflict"
          else
            LABEL="clean-merge"
          fi
          # PR erstellen (gh pr create)
```

**Logik**:
1. Job läuft wöchentlich
2. Vergleicht latest `upstream-v*`-Tag mit unserem letzten `upstream/v*`-Tag
3. Wenn neuer → branch `sync/upstream-vX.Y.Z` + `git merge` versuchen
4. PR erstellen mit Labels: `clean-merge` (auto-mergeable) oder `needs-review-conflict`
5. Maintainer reviewt + merged, dann Tag `upstream/vX.Y.Z` setzen + ggf. `v1.X.Y` Release

### Files

- **Neu**: `.github/workflows/upstream-sync.yml` (~80 Zeilen Bash + YAML)
- **Neu**: `docs/upstream-sync-process.md` — schriftlicher Prozess für Maintainer (was tun bei Konflikt-PR, wann Workplace-Release danach)

### Verifikation

| Test | Erwartet |
|---|---|
| `workflow_dispatch` manuell triggern bei aktuellem Stand | „nothing to sync" — kein PR |
| `workflow_dispatch` triggern wenn Mistral neues Release | PR erstellt, Label gesetzt |
| Konflikt in Adacor-Patch | Label `needs-review-conflict` |
| Sauberer Merge | Label `clean-merge`, optional Auto-Merge-Rule (Branch-Protection) |

### Aufwand

~3h. Action-Logik + Test-Run + Doku.

### Risiken

- **Mistral macht zwei Releases pro Woche** → Sync-Job kollidiert mit sich selbst. Mitigation: vor dem Branch-Anlegen prüfen, ob `sync/*`-Branch schon existiert
- **Branch-Pollution** — alte sync-Branches stehen rum. Mitigation: Action löscht alte `sync/*`-Branches die >30 Tage alt und gemerged sind
- **Konflikt-Marker-Erkennung** ist Best-Effort — manche Patches könnten Konflikte AUSSERHALB der Marker erzeugen. Maintainer-Review bleibt Pflicht

---

## Phasen-Reihenfolge & Empfehlung

```
P2 (Provider/Model-Config)   ──┐
                               ├─→ direkt sinnvoll, low-risk, hoher User-Value
P3 (Update-Check)            ──┘   (P2 macht Defaults konfigurierbar,
                                    P3 informiert User über neue Versionen)

P5 (Auto-Sync)               ──→ Maintainer-Komfort, sobald P2 etabliert
                                  (weniger Konfliktpotential bei Sync)

P4 (SSO)                     ──→ braucht DevOps-Vorarbeit (Adacor-Identity-OIDC)
                                  → zeitlich entkoppeln
```

**Vorschlag**: P2 + P3 als nächste Iteration (zusammen ~6h Code-Work) → eigenes Release `v1.1.0`. P5 danach. P4 wenn Adacor-Identity-OIDC verfügbar.

---

## Phase 1 — Was schon live ist (Referenz)

| Komponente | Status |
|---|---|
| Repo `tilweb/workplace-cli` (public, Apache-2.0) | ✓ |
| Release `v1.0.0` mit Wheel + sdist | ✓ |
| Homebrew-Tap `tilweb/homebrew-tap` | ✓ |
| `brew tap tilweb/tap && brew install workplace-cli` funktioniert | ✓ CI-grün |
| `uv tool install git+https://github.com/tilweb/workplace-cli` | ✓ |
| Branding (Banner, Persona, Farben, Binary-Name `workplace`) | ✓ |
| Telemetrie-Default `off`, Mistral-Endpoint raus | ✓ |
| Apache-2.0-Compliance (`NOTICE`, README-Attribution, CHANGELOG-Trennung) | ✓ |
| CI (`lint + build + smoke`) | ✓ |
| Release-Pipeline (Tag `v*` → GitHub-Release mit Wheel) | ✓ |
| Tap-CI (`brew install` + funktionaler Test auf macOS-VM) | ✓ |

5 thematisch saubere Commits + 2 Tags (`v1.0.0`, `upstream/v2.9.4`) auf `main`. Patches mit `# === ADACOR PATCH START/END ===`-Markern in den 5 kritischen Source-Files.
