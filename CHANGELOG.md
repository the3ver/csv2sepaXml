# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/)
und dieses Projekt folgt den Richtlinien von [Semantic Versioning](https://semver.org/lang/de/).

---

## [0.3.1] - 2026-09-12

### Behoben & Verbessert
- **Vermeidung von Windows 11 SmartScreen & „Unbekannter Herausgeber“-Warnungen**:
  - **1-Klick Starter (`start_app.bat`)**: Bequemes Starterskript direkt neben der `.exe`, das den Windows-Download-Hinweis (*Mark of the Web* / `Zone.Identifier`) per `Unblock-File` automatisch entfernt und das Programm ohne störenden Dialog öffnet.
  - **Digitale Authenticode-Signierung (`scripts/sign_exe.ps1`)**: Signiert `dist\csv2sepaXml.exe` automatisch mit Authenticode-Zertifikat und DigiCert-Zeitstempel. Datei-Eigenschaften weisen den Herausgeber `the3ver` aus.
  - **PyInstaller-Härtung**: Kompilierung mit `--noupx`, um heuristische Fehlalarme von Antivirenprogrammen auszuschließen.
  - **Begleitdateien in `dist/`**: Automatisches Bereitstellen von `start_app.bat`, `config.example.json` und `sample_mitglieder.csv` für sofortige Einsatzbereitschaft.
  - **Dokumentation**: Ausführliche Hilfestellung mit Dialog-Illustration in der Online-Anleitung (`docs/index.html`) und im `README.md`.

---

## [0.3.0] - 2026-09-12

### Hinzugefügt
- **Automatische Erkennung von `config.json` neben der `.exe`**:
  - Liegt eine `config.json` direkt im Verzeichnis der ausführbaren Datei (`csv2sepaXml.exe`), werden die Vereins- und Gläubigerdaten automatisch daraus geladen – selbst wenn das Programm aus einem anderen Arbeitsverzeichnis oder per Desktop-Verknüpfung gestartet wird.
  - Das Speichern der Konfiguration im Web-Interface (`Im Browser speichern`) sichert die Einstellungen nun ebenfalls automatisch direkt neben der `.exe`.
  - Entwickler-Fallback: Aufrufe per Skript (`python sepa_generator.py`) durchsuchen weiterhin wie gewohnt das aktuelle Arbeitsverzeichnis.

---

## [0.2.0] - 2026-09-12

### Hinzugefügt
- **Eigenständige Windows-App (`csv2sepaXml.exe`)**:
  - Startet per Doppelklick ohne Python-Installation direkt im Browser.
  - Windows-Versionsressource in der `.exe` verankert (Dateiversion: `0.2.0.0`, Produktname: `csv2sepaXml`).
- **Lokale Browser-Oberfläche**:
  - Intuitive Weboberfläche mit Drag & Drop CSV-Dateiupload.
  - Statusanzeige sofort beim Ablegen oder Auswählen einer Datei.
  - Echtzeit-Statistiken (geladene Datensätze, gültige Lastschriften, fehlerhafte Datensätze, Gesamteinzugssumme).
  - Interaktive Prüftabelle mit Filter-Reitern (*Alle*, *Nur Gültige*, *Fehlerhafte*).
  - 1-Klick-Download für die generierte XML-Datei und das Prüfprotokoll.
- **SEPA-Konformität (pain.008.001.08)**:
  - Vollständige Unterstützung des aktuellen ISO 20022 EPC SEPA Standards `pain.008.001.08` (ab 2024/2025).
  - Standard-Sequenztyp `RCUR` (wiederkehrend / Folgelastschrift) sowie Unterstützung für `FRST`, `OOFF` und `FNAL`.
  - Optionale BIC-Behandlung für DE/EWR-Konten gemäß SEPA-Verordnung (IBAN-Only).
  - Sammelbuchungskennzeichen (`<BtchBookg>true</BtchBookg>`) für Einzel- oder Sammelposten auf dem Kontoauszug.
  - Automatische Validierung gegen das offizielle ISO 20022 Schema (`schema/pain.008.001.08.xsd`).
  - SEPA-Zeichensatzkonforme Bereinigung von Umlauten und Sonderzeichen.
- **Intelligenter CSV-Parser**:
  - Automatische Trennzeichenerkennung (Semikolon `;`, Komma `,`, Tabulator).
  - Flexible Erkennung deutscher Spaltenüberschriften (z.B. *„Beitrag in Euro“*, *„Betrag“*, *„Mandatsreferenz“*, *„Mandatsdatum“*).
  - Automatische Bereinigung von Leerzeichen in IBANs (z.B. `DE69 5001 0517 ...`).
  - Unterstützung für deutsche Zahlenformate (z.B. `25,00 €`).
  - Automatische Zeichensatzerkennung (UTF-8, UTF-8-BOM, CP1252 / Windows-1252).
- **Validierung & Sicherheit**:
  - Modulo-97 IBAN-Prüfsummenberechnung (ISO 7064).
  - Gläubiger-ID-Prüfung.
  - Revisionssicheres Kassenprüf-Protokoll (`sepa_einzugsprotokoll_*.txt`) mit SHA-256 Prüfsumme und Gesamtkontrolle für Kassenprüfer.
  - Datenschutzkonforme, rein technische Debug-Logdatei (`vereinseinzug.log`) ohne personenbezogene Daten.
- **Dokumentation & Community**:
  - Schritt-für-Schritt Online-Anleitung für GitHub Pages (`docs/index.html`) inklusive Screenshots.
  - Offizielle Open-Source-Lizenzierung unter der **MIT-Lizenz** (`LICENSE`).
