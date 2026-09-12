"""
Command line interface for vereinseinzug.
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from .config import ClubConfig
from .parser import parse_csv_file, generate_sample_csv
from .generator import SepaPain008Generator
from .web import run_web_server
from .logger import logger
from .protocol import generate_audit_protocol


def main():
    parser = argparse.ArgumentParser(
        description="SEPA Lastschrift pain.008.001.08 XML-Generator für Vereine"
    )

    parser.add_argument(
        "--web",
        action="store_true",
        help="Startet die lokale Weboberfläche im Browser",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port für die Weboberfläche (Standard: 8080)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Browser beim Starten der Web-UI nicht automatisch öffnen",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="Pfad zur Mitglieder-CSV-Datei",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.json"),
        help="Pfad zur Vereins-Konfigurationsdatei (Standard: config.json)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Pfad für die zu erstellende XML-Datei (z.B. einzug.xml)",
    )
    parser.add_argument(
        "--sample-csv",
        nargs="?",
        const="mitglieder_vorlage.csv",
        help="Erstellt eine Muster-CSV-Vorlage (optionaler Dateiname, Standard: mitglieder_vorlage.csv)",
    )
    parser.add_argument(
        "--init-config",
        nargs="?",
        const="config.json",
        help="Erstellt eine Vorlage für config.json",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="CSV-Datei und Daten nur prüfen, keine XML schreiben",
    )

    # Direct config overrides via CLI
    parser.add_argument("--creditor-name", help="Vereinsname (Gläubiger)")
    parser.add_argument("--creditor-id", help="Gläubiger-ID (z.B. DE98ZZZ09999999999)")
    parser.add_argument("--creditor-iban", help="Vereins-IBAN")
    parser.add_argument("--creditor-bic", help="Vereins-BIC (optional)")
    parser.add_argument("--collection-date", help="Fälligkeitsdatum (JJJJ-MM-TT)")
    parser.add_argument("--sequence-type", choices=["RCUR", "FRST", "OOFF", "FNAL"], default=None, help="Sequenztyp (Standard: RCUR)")
    parser.add_argument("--remittance", help="Standard-Verwendungszweck")

    args = parser.parse_args()

    # 1. Action: Sample CSV
    if args.sample_csv:
        target_path = Path(args.sample_csv)
        csv_content = generate_sample_csv()
        with open(target_path, "w", encoding="utf-8-sig") as f:
            f.write(csv_content)
        print(f"[OK] Muster-CSV erfolgreich erstellt: {target_path.resolve()}")
        sys.exit(0)

    # 2. Action: Init config
    if args.init_config:
        target_path = Path(args.init_config)
        cfg = ClubConfig(
            creditor_name="Sportverein Musterstadt e.V.",
            creditor_id="DE98ZZZ09999999999",
            creditor_iban="DE89370400440532013000",
            creditor_bic="BYLADEM1001",
            collection_date=(date.today() + timedelta(days=7)).isoformat(),
            sequence_type="RCUR",
            default_remittance="Mitgliedsbeitrag 2026",
            batch_booking=True,
        )
        cfg.save_to_file(target_path)
        print(f"[OK] Konfigurationsvorlage erstellt: {target_path.resolve()}")
        sys.exit(0)

    # 3. Action: Web UI
    if args.web or (len(sys.argv) == 1 and not args.csv):
        print("Starte SEPA Lastschrift Web-UI...")
        run_web_server(port=args.port, open_browser=not args.no_browser)
        sys.exit(0)

    # 4. Action: Process CSV
    if not args.csv:
        print("[FEHLER] Bitte geben Sie eine CSV-Datei mit '--csv <pfad>' an oder starten Sie die Web-UI mit '--web'.")
        parser.print_help()
        sys.exit(1)

    csv_path = args.csv
    if not csv_path.is_file():
        print(f"[FEHLER] Datei nicht gefunden: {csv_path}")
        sys.exit(1)

    # Load or build config
    if args.config.is_file():
        config = ClubConfig.load_from_file(args.config)
    else:
        config = ClubConfig()

    # Apply command line overrides
    if args.creditor_name: config.creditor_name = args.creditor_name
    if args.creditor_id: config.creditor_id = args.creditor_id
    if args.creditor_iban: config.creditor_iban = args.creditor_iban
    if args.creditor_bic: config.creditor_bic = args.creditor_bic
    if args.collection_date: config.collection_date = args.collection_date
    if args.sequence_type: config.sequence_type = args.sequence_type
    if args.remittance: config.default_remittance = args.remittance

    print(f"Lese CSV-Datei: {csv_path}")
    logger.info("Reading CSV file: %s", csv_path.name)
    payments, stats = parse_csv_file(csv_path, default_remittance=config.default_remittance)

    if "error" in stats:
        logger.error("CSV parse error: %s", stats["error"])
        print(f"[FEHLER] {stats['error']}")
        sys.exit(1)

    logger.info("CSV parsed: %d total records, %d valid, %d invalid, delimiter '%s'",
                stats['total_records'], stats['valid_records'], stats['invalid_records'], stats['delimiter_detected'])

    print(f"-> {stats['total_records']} Datensätze gefunden (Trennzeichen: '{stats['delimiter_detected']}')")
    print(f"-> {stats['valid_records']} gültig, {stats['invalid_records']} fehlerhaft")
    print(f"-> Gesamtsumme: {stats['total_amount_formatted']}")

    # Display warnings and errors
    invalid_payments = [p for p in payments if not p.is_valid]
    if invalid_payments:
        print("\n[ACHTUNG] Folgende Datensätze enthalten Fehler und werden NICHT eingezogen:")
        for p in invalid_payments:
            print(f"  Zeile {p.row_number} ({p.name}, IBAN: {p.iban}):")
            for err in p.errors:
                print(f"    - {err}")
            logger.warning("Record row %d invalid: %s", p.row_number, "; ".join(p.errors))

    warned_payments = [p for p in payments if p.warnings and p.is_valid]
    if warned_payments:
        print("\n[HINWEIS] Bereinigungen / Warnungen:")
        for p in warned_payments:
            print(f"  Zeile {p.row_number} ({p.name}):")
            for w in p.warnings:
                print(f"    - {w}")

    if args.validate_only:
        print("\n[OK] Validierung abgeschlossen.")
        logger.info("Validation-only check completed.")
        sys.exit(0 if not invalid_payments else 1)

    # Validate configuration
    cfg_errors = config.validate()
    if cfg_errors:
        logger.error("Configuration validation error: %s", "; ".join(cfg_errors))
        print("\n[FEHLER] Vereinsdaten (Gläubiger) unvollständig:")
        for err in cfg_errors:
            print(f"  - {err}")
        print("\nBitte passen Sie 'config.json' an oder übergeben Sie die Parameter als CLI-Argumente.")
        sys.exit(1)

    valid_payments = [p for p in payments if p.is_valid]
    if not valid_payments:
        logger.error("No valid debit transactions available to create XML.")
        print("\n[FEHLER] Keine gültigen Lastschriften zum Erstellen der XML-Datei vorhanden.")
        sys.exit(1)

    # Output file path
    if not args.output:
        today_str = date.today().strftime("%Y%m%d")
        output_file = Path(f"sepa_lastschrift_pain008_{today_str}.xml")
    else:
        output_file = args.output

    print("\nErstelle pain.008.001.08 XML-Datei...")
    logger.info("Generating pain.008.001.08 XML for %d transactions...", len(valid_payments))
    generator = SepaPain008Generator(config)
    xml_str = generator.generate_xml(valid_payments)

    print("Validiere XML gegen ISO 20022 Schema (pain.008.001.08.xsd)...")
    is_valid, schema_errors = generator.validate_xml_schema(xml_str)
    if not is_valid:
        logger.error("Schema validation failed: %s", "; ".join(schema_errors))
        print("\n[FEHLER] Schemavalidierung fehlgeschlagen:")
        for err in schema_errors:
            print(f"  - {err}")
        sys.exit(1)

    logger.info("Schema validation successful (pain.008.001.08 compliant).")
    print("[OK] Schema-Validierung erfolgreich (100% konform zu pain.008.001.08)!")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(xml_str)
    logger.info("XML written to %s", output_file.name)

    # Generate and save club audit protocol
    protocol_file = output_file.with_suffix(".protokoll.txt")
    protocol_text = generate_audit_protocol(config, payments, stats, xml_filename=output_file.name)
    with open(protocol_file, "w", encoding="utf-8") as f:
        f.write(protocol_text)
    logger.info("Audit protocol written to %s", protocol_file.name)

    print(f"\n=======================================================")
    print(f" [ERFOLG] SEPA-XML erfolgreich erstellt:")
    print(f" XML-Datei:  {output_file.resolve()}")
    print(f" Protokoll:  {protocol_file.resolve()}")
    print(f" Einzüge:    {len(valid_payments)} Posten")
    print(f" Summe:      {stats['total_amount_formatted']}")
    print(f" Fälligkeit: {config.collection_date}")
    print(f" Gläubiger:  {config.creditor_name} ({config.creditor_id})")
    print(f"=======================================================\n")


if __name__ == "__main__":
    main()
