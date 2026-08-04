# Neu in Workplace CLI 1.1

- **Vision — Bilder & PDFs**: Der Agent kann jetzt Bilder und PDFs *sehen*. Datei per `@bild.png` anhängen, per Copy & Paste einfügen, oder den Agent selbst per `read_file` öffnen lassen (PDF-Seiten werden gerendert). Default-Modell `qwen3.5-35b` ist vision-fähig.
- **Datei per Copy & Paste anhängen**: Eine eingefügte Datei wird automatisch als `@`-Anhang übernommen (Drag & Drop in Terminals wie iTerm2, die Drops als Paste senden).
- **Modell-Picker aufgeräumt**: Nur noch Adacor (live entdeckt) und lokale Modelle — Mistral ist raus.
- **Updates: nur Hinweis**: Kein stilles Selbst-Update mehr; bei einer neuen Version zeigt Workplace CLI einen Hinweis mit dem Upgrade-Befehl.
