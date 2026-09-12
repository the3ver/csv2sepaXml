"""
Data models and SEPA character set sanitization.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Dict, Any

from .iban import clean_iban, clean_bic, validate_iban, validate_bic

# SEPA permitted characters:
# a-z A-Z 0-9 / - ? : ( ) . , ' + [space]
SEPA_ALLOWED_CHARS_RE = re.compile(r"[^A-Za-z0-9/\-?:().,'+ ]")


def sanitize_sepa_text(text: str, max_length: int = 70) -> str:
    """
    Sanitize text according to SEPA character set guidelines:
    - Replace German umlauts (ä->ae, ö->oe, ü->ue, ß->ss)
    - Normalize accents (é->e, etc.)
    - Replace & with +
    - Filter disallowed characters
    - Truncate to max_length
    """
    if not text:
        return ""

    s = str(text).strip()

    # Umlaut replacements
    replacements = {
        "ä": "ae", "ö": "oe", "ü": "ue",
        "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
        "ß": "ss",
        "&": "+",
    }
    for orig, rep in replacements.items():
        s = s.replace(orig, rep)

    # Normalize unicode accents (NFD decomposes e.g. é into e + accent, then strip accents)
    s = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

    # Remove any characters not allowed in SEPA
    s = SEPA_ALLOWED_CHARS_RE.sub(" ", s)

    # Collapse multiple consecutive spaces
    s = re.sub(r"\s+", " ", s).strip()

    return s[:max_length]


@dataclass
class MemberPayment:
    name: str
    iban: str
    bic: Optional[str] = None
    amount: Decimal = Decimal("0.00")
    mandate_id: str = ""
    mandate_date: Optional[str] = None  # YYYY-MM-DD
    remittance: str = ""
    end_to_end_id: str = ""
    row_number: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def validate(self) -> None:
        """Validate this record and populate errors and warnings."""
        self.errors.clear()
        self.warnings.clear()

        # Name check
        clean_name = self.name.strip()
        if not clean_name:
            self.errors.append("Zahlungspflichtiger / Name fehlt.")
        else:
            sanitized_name = sanitize_sepa_text(clean_name, max_length=70)
            if sanitized_name != clean_name:
                self.warnings.append(f"Name bereinigt für SEPA: '{sanitized_name}'")
            if len(sanitized_name) == 0:
                self.errors.append("Name enthält keine gültigen Zeichen.")

        # IBAN check
        cleaned_iban = clean_iban(self.iban)
        if not cleaned_iban:
            self.errors.append("IBAN fehlt.")
        else:
            is_valid, msg = validate_iban(cleaned_iban)
            if not is_valid:
                self.errors.append(msg)
            self.iban = cleaned_iban

        # BIC check
        if self.bic:
            cleaned_bic = clean_bic(self.bic)
            if cleaned_bic:
                is_valid, msg = validate_bic(cleaned_bic)
                if not is_valid:
                    self.errors.append(msg)
                self.bic = cleaned_bic
            else:
                self.bic = None

        # Amount check
        if self.amount <= Decimal("0.00"):
            self.errors.append(f"Betrag muss größer als 0,00 € sein (aktuell: {self.amount:.2f} €).")
        elif self.amount > Decimal("999999999.99"):
            self.errors.append("Betrag übersteigt das SEPA-Limit.")

        # Mandate ID check
        clean_mndt = sanitize_sepa_text(self.mandate_id.strip(), max_length=35)
        if not clean_mndt:
            self.errors.append("Mandatsreferenz fehlt.")
        else:
            self.mandate_id = clean_mndt

        # Mandate Date check
        if not self.mandate_date:
            self.errors.append("Mandatsdatum (Unterschriftsdatum) fehlt.")
        else:
            try:
                # Accept YYYY-MM-DD or try to parse other common formats
                parsed_dt = parse_flexible_date(self.mandate_date)
                if parsed_dt > date.today():
                    self.warnings.append(f"Mandatsdatum liegt in der Zukunft ({parsed_dt.isoformat()}).")
                self.mandate_date = parsed_dt.isoformat()
            except ValueError as e:
                self.errors.append(f"Ungültiges Mandatsdatum: '{self.mandate_date}' (Format: JJJJ-MM-TT oder TT.MM.JJJJ)")

        # EndToEndId
        if not self.end_to_end_id:
            # Generate fallback EndToEndId from mandate_id or row
            self.end_to_end_id = sanitize_sepa_text(f"E2E-{self.mandate_id[:25]}-{self.row_number}", max_length=35)
        else:
            self.end_to_end_id = sanitize_sepa_text(self.end_to_end_id, max_length=35)

        # Remittance info
        if self.remittance:
            self.remittance = sanitize_sepa_text(self.remittance, max_length=140)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_number": self.row_number,
            "name": self.name,
            "iban": self.iban,
            "bic": self.bic or "",
            "amount": float(self.amount),
            "amount_formatted": f"{self.amount:.2f} €".replace(".", ","),
            "mandate_id": self.mandate_id,
            "mandate_date": self.mandate_date or "",
            "remittance": self.remittance,
            "end_to_end_id": self.end_to_end_id,
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def parse_flexible_date(date_str: str) -> date:
    """Parse a date string in DD.MM.YYYY, YYYY-MM-DD, or DD/MM/YYYY."""
    s = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unbekanntes Datumsformat: {date_str}")
