"""
CSV Parser with flexible column mapping, delimiter autodetection, and encoding support.
"""

import csv
import io
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

from .models import MemberPayment


# Canonical column mappings (lowercase, stripped, without underscores/hyphens)
COLUMN_ALIASES = {
    "name": [
        "name", "mitglied", "kontoinhaber", "mitgliedsname", "vollername",
        "fullname", "debtor", "zahler", "empfaenger"
    ],
    "first_name": ["vorname", "firstname", "first_name"],
    "last_name": ["nachname", "lastname", "last_name", "familienname"],
    "iban": ["iban", "kontonummer", "iban-nummer", "ibannummer", "account"],
    "bic": ["bic", "swift", "bic-code", "biccode", "swift-bic"],
    "amount": [
        "betrag", "beitrag", "amount", "summe", "jahresbeitrag",
        "mitgliedsbeitrag", "spende", "kosten", "gebuehr"
    ],
    "mandate_id": [
        "mandatsreferenz", "mandatsnummer", "mandat", "mitgliedsnummer",
        "mandate_id", "mandat_id", "mandats_id", "mndtid", "mandatsref"
    ],
    "mandate_date": [
        "mandatsdatum", "unterschriftsdatum", "mandat_datum", "mandats_datum",
        "mandatedate", "mandate_date", "datum_mandat", "datum"
    ],
    "remittance": [
        "verwendungszweck", "zweck", "bemerkung", "buchungstext",
        "remittance", "verwendungszweck1", "text"
    ],
    "end_to_end_id": ["end_to_end_id", "e2e_id", "referenz", "endtoendid"],
}


def normalize_header(h: str) -> str:
    """Normalize a header string for matching."""
    s = str(h).strip().lower()
    s = re.sub(r"[\s\-_]+", "", s)
    return s


def parse_amount(val: Any) -> Decimal:
    """
    Parse a numeric string into Decimal.
    Supports German format '50,00 €', '1.250,50' and standard '50.00'.
    """
    if val is None:
        return Decimal("0.00")

    s = str(val).strip().replace("€", "").replace("EUR", "").strip()
    if not s:
        return Decimal("0.00")

    # If comma and dot both present: e.g. 1.250,50 or 1,250.50
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            # German 1.250,50 -> 1250.50
            s = s.replace(".", "").replace(",", ".")
        else:
            # English 1,250.50 -> 1250.50
            s = s.replace(",", "")
    elif "," in s:
        # Only comma: e.g. 50,00 -> 50.00
        s = s.replace(",", ".")

    try:
        dec = Decimal(s)
        return dec.quantize(Decimal("0.01"))
    except InvalidOperation:
        return Decimal("0.00")


def detect_delimiter(sample_text: str) -> str:
    """Autodetect whether semicolon, comma, or tab is used."""
    counts = {
        ";": sample_text.count(";"),
        ",": sample_text.count(","),
        "\t": sample_text.count("\t"),
    }
    # Pick the one with the highest count, defaulting to semicolon for German CSVs
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ";"


def find_column_map(headers: List[str]) -> Dict[str, int]:
    """
    Map canonical field names to column indices in headers.
    """
    norm_headers = [normalize_header(h) for h in headers]
    col_map: Dict[str, int] = {}

    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            norm_alias = normalize_header(alias)
            if norm_alias in norm_headers:
                col_map[canonical] = norm_headers.index(norm_alias)
                break

    return col_map


def parse_csv_content(
    content: str,
    default_remittance: str = "Mitgliedsbeitrag",
    default_mandate_date: Optional[str] = None,
) -> Tuple[List[MemberPayment], Dict[str, Any]]:
    """
    Parse CSV string content into MemberPayment objects with validation.
    Returns (payments_list, stats_dict).
    """
    delimiter = detect_delimiter(content[:2048])
    reader = csv.reader(io.StringIO(content), delimiter=delimiter)

    rows = list(reader)
    if not rows:
        return [], {"error": "CSV-Datei ist leer."}

    header_row = rows[0]
    col_map = find_column_map(header_row)

    # Validate essential columns
    has_name = "name" in col_map or ("first_name" in col_map and "last_name" in col_map)
    has_iban = "iban" in col_map
    has_amount = "amount" in col_map

    missing = []
    if not has_name:
        missing.append("Name (oder Vorname + Nachname)")
    if not has_iban:
        missing.append("IBAN")
    if not has_amount:
        missing.append("Betrag")

    if missing:
        return [], {
            "error": f"Erforderliche Spalten nicht gefunden: {', '.join(missing)}. "
                     f"Gefundene Spalten: {', '.join(header_row)}"
        }

    payments: List[MemberPayment] = []

    for row_idx, row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in row):
            continue  # Skip blank rows

        def get_val(key: str, default: str = "") -> str:
            idx = col_map.get(key)
            if idx is not None and idx < len(row):
                return row[idx].strip()
            return default

        # Determine Name
        if "first_name" in col_map and "last_name" in col_map:
            first = get_val("first_name")
            last = get_val("last_name")
            name = f"{first} {last}".strip()
        elif "name" in col_map:
            name = get_val("name")
        elif "last_name" in col_map:
            name = get_val("last_name")
        else:
            name = get_val("first_name")

        iban = get_val("iban")
        bic = get_val("bic") or None
        amount = parse_amount(get_val("amount"))

        # Mandate ID (fallback to Mitgliedsnummer or auto M-Row if empty)
        mandate_id = get_val("mandate_id")
        if not mandate_id:
            mandate_id = f"M-{row_idx}"

        # Mandate Date
        mandate_date = get_val("mandate_date")
        if not mandate_date and default_mandate_date:
            mandate_date = default_mandate_date

        # Remittance info
        remittance = get_val("remittance")
        if not remittance:
            remittance = default_remittance

        e2e_id = get_val("end_to_end_id")

        payment = MemberPayment(
            name=name,
            iban=iban,
            bic=bic,
            amount=amount,
            mandate_id=mandate_id,
            mandate_date=mandate_date,
            remittance=remittance,
            end_to_end_id=e2e_id,
            row_number=row_idx,
        )
        payment.validate()
        payments.append(payment)

    total_amount = sum((p.amount for p in payments), Decimal("0.00"))
    valid_count = sum(1 for p in payments if p.is_valid)
    invalid_count = len(payments) - valid_count

    stats = {
        "total_records": len(payments),
        "valid_records": valid_count,
        "invalid_records": invalid_count,
        "total_amount": float(total_amount),
        "total_amount_formatted": f"{total_amount:.2f} €".replace(".", ","),
        "delimiter_detected": delimiter,
        "columns_found": list(col_map.keys()),
    }

    return payments, stats


def parse_csv_file(
    filepath: Path,
    default_remittance: str = "Mitgliedsbeitrag",
    default_mandate_date: Optional[str] = None,
) -> Tuple[List[MemberPayment], Dict[str, Any]]:
    """Parse a CSV file with automatic encoding fallback."""
    content: str = ""
    encodings = ["utf-8-sig", "utf-8", "cp1252", "iso-8859-1"]

    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue

    if not content:
        return [], {"error": f"Konnte Datei '{filepath}' nicht lesen (Zeichenkodierungsfehler)."}

    return parse_csv_content(
        content=content,
        default_remittance=default_remittance,
        default_mandate_date=default_mandate_date,
    )


def generate_sample_csv() -> str:
    """Generate sample CSV content for club members."""
    rows = [
        ["Name", "IBAN", "BIC", "Betrag", "Mandatsreferenz", "Mandatsdatum", "Verwendungszweck"],
        ["Max Mustermann", "DE89370400440532013000", "BYLADEM1001", "60,00", "M-00101", "2022-03-15", "Jahresbeitrag 2026"],
        ["Erika Musterfrau", "DE16120300000123456789", "", "45,50", "M-00102", "2023-01-10", "Mitgliedsbeitrag ermässigt"],
        ["Hans Meier", "DE44500105175407324931", "", "120,00", "M-00103", "2021-07-01", "Familienbeitrag 2026"],
    ]
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerows(rows)
    return output.getvalue()
