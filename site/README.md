# Ergebnis-Website

Statische Astro-Seite mit den Ergebnissen des Projekts (deutsch): Zahlen, Grafiken, Lernpfad, Tracker- und Modellvergleiche,
Test-Details und ein Bahnen-Viewer. Veröffentlicht auf GitHub Pages:
https://florianditt.github.io/honeybee-orientation-flight-classification/

Die Seite enthält nur Zahlen, Labels, Bahnkoordinaten und Diagramme. **Keine Videos, Clips, Einzelbilder oder Ausschnitte** aus dem
gated Datensatz, keine Namen von Labelnden (nur „Florian“, „Labeler 2“, „Labeler 3“).

## Benutzung

```bash
npm install
npm run snapshot   # nur lokal: liest ../outputs und ../labels und schreibt src/data/*.json (Selbstcheck auf verbotene Inhalte)
npm run dev        # Entwicklung
npm run build      # statische Seite nach dist/
npm run check      # Typprüfung
```

`npm run snapshot` braucht die lokalen Ordner `outputs/` und `labels/` und gehört deshalb nicht zum CI-Build. Die Snapshot-Dateien in
`src/data/` sind eingecheckt, der Build (GitHub Actions, `.github/workflows/pages.yml`) braucht nur diese. Die Basis-URL steht in
`astro.config.mjs` (`SITE_BASE`, Standard `/honeybee-orientation-flight-classification`).

Die Testergebnisse werden nur kopiert (`outputs/final/test_ergebnis.json`, `outputs/eval/test_*/summary.json`), nie neu berechnet.

## Lizenz

Texte, Grafiken und Daten dieser Seite: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/), Namensnennung
„Schutera, Mark, thehiveisreal (2026)“. Code: MIT.
