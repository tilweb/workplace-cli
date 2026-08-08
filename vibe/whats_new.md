# Neu in Workplace CLI 1.4

- **MCP-Server einfach einrichten**: Externe Tools (z.B. YouTrack, GitLab) anbinden ohne Datei-Editieren — per `workplace mcp add …` (plus `list`/`remove`) oder im TUI über `/mcp add`. Tokens bleiben in Env-Variablen.

## Weiterhin aus 1.3

- **Hintergrund-Prozesse** (`bash`): Langläufer wie Dev-Server, `tail -f` oder Watcher mit `run_in_background` starten, ohne die Session zu blockieren — Output per `bash_output` nachlesen, per `kill_bash` stoppen.
- **Design-Skills mit visueller Kontrolle**: `/frontend-design` und `/canvas-design` rendern ihr Ergebnis jetzt per `screenshot` und *sehen* es an, statt Design nur aus dem Code zu beurteilen.
- **Theme-Übersicht** (`/theme-factory`): Eine mitgelieferte Showcase-PDF zeigt alle 10 Farb-/Schrift-Themes visuell — auf einen Blick wählbar.

## Weiterhin aus 1.2

- **Office-Dokumente erstellen** (`/document-builder`): Word, Excel, PowerPoint und PDF aus Inhalten/Daten — in neutralem Standarddesign, ohne API oder Internet.
- **Screenshots & visuelle Prüfung** (`screenshot`): Der Agent rendert eine URL oder lokale HTML-Datei und *sieht* das Ergebnis (Vision) — praktisch zum Kontrollieren von Frontend-Arbeit. Chromium einmalig via `playwright install chromium`.
- **Gedächtnis über Sessions** (`remember`): Der Agent kann sich dauerhafte Fakten merken (Vorlieben, Projekt-Konventionen) und erinnert sie in späteren Sessions.
- **Dateien schnell finden** (`glob`): Suche nach Namensmuster wie `**/*.py`, ergänzend zur Inhaltssuche (`grep`).

## Weiterhin aus 1.1

- **Vision — Bilder & PDFs**: Bilder und PDFs anhängen (`@bild.png`, Copy & Paste) oder vom Agent per `read_file` öffnen lassen. Default-Modell `qwen3.5-35b` ist vision-fähig.
- **Modell-Picker**: Nur Adacor (live entdeckt) und lokale Modelle — Mistral ist raus.
- **Updates: nur Hinweis** — kein stilles Selbst-Update.
