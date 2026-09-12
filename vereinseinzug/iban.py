"""
IBAN and BIC validation according to ISO 13616 and ISO 7064.
"""

import re
from typing import Tuple, Optional

# Country code to expected IBAN length in SEPA zone & common countries
IBAN_LENGTHS = {
    "AL": 28, "AD": 24, "AT": 20, "BE": 16, "BA": 20, "BG": 22, "HR": 21,
    "CY": 28, "CZ": 24, "DK": 18, "EE": 20, "FI": 18, "FR": 27, "DE": 22,
    "GI": 23, "GR": 27, "HU": 28, "IS": 26, "IE": 22, "IT": 27, "LV": 21,
    "LI": 21, "LT": 20, "LU": 20, "MT": 31, "MC": 27, "ME": 22, "NL": 18,
    "MK": 19, "NO": 15, "PL": 28, "PT": 25, "RO": 24, "SM": 27, "RS": 22,
    "SK": 24, "SI": 19, "ES": 24, "SE": 24, "CH": 21, "GB": 22, "VA": 22,
}

BIC_REGEX = re.compile(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")
CREDITOR_ID_REGEX = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{3}[A-Z0-9]{1,28}$")


def clean_iban(iban: str) -> str:
    """Remove spaces, hyphens, and convert to uppercase."""
    if not iban:
        return ""
    return re.sub(r"[\s\-]", "", str(iban).strip().upper())


def clean_bic(bic: Optional[str]) -> Optional[str]:
    """Remove spaces, hyphens, and convert to uppercase."""
    if not bic:
        return None
    cleaned = re.sub(r"[\s\-]", "", str(bic).strip().upper())
    return cleaned if cleaned else None


def validate_iban(iban: str) -> Tuple[bool, str]:
    """
    Validate an IBAN with Modulo 97 (ISO 7064).
    Returns (is_valid, error_message).
    """
    cleaned = clean_iban(iban)
    if not cleaned:
        return False, "IBAN darf nicht leer sein"

    if len(cleaned) < 5 or len(cleaned) > 34:
        return False, f"IBAN-Länge ungültig ({len(cleaned)} Zeichen)"

    country_code = cleaned[:2]
    if not country_code.isalpha():
        return False, f"Ländercode ungültig: {country_code}"

    # Check country-specific length if known
    expected_length = IBAN_LENGTHS.get(country_code)
    if expected_length and len(cleaned) != expected_length:
        return False, f"IBAN für {country_code} muss {expected_length} Zeichen haben (hat {len(cleaned)})"

    if not cleaned.isalnum():
        return False, "IBAN enthält unzulässige Sonderzeichen"

    # Move first 4 characters to the end
    rearranged = cleaned[4:] + cleaned[:4]

    # Convert letters to digits: A -> 10, B -> 11, ..., Z -> 35
    digits = []
    for char in rearranged:
        if char.isdigit():
            digits.append(char)
        elif char.isalpha():
            digits.append(str(ord(char) - ord("A") + 10))
        else:
            return False, "Ungültiges Zeichen in IBAN"

    num_str = "".join(digits)
    try:
        remainder = int(num_str) % 97
    except ValueError:
        return False, "Fehler bei Modulo-97-Berechnung"

    if remainder != 1:
        return False, "IBAN-Prüfsumme ist falsch (Zahlendreher oder Tippfehler)"

    return True, ""


def validate_bic(bic: Optional[str]) -> Tuple[bool, str]:
    """
    Validate a BIC/SWIFT code (8 or 11 characters).
    Optional in SEPA IBAN-only rule, but must match standard format if provided.
    """
    if not bic:
        return True, ""
    cleaned = clean_bic(bic)
    if not cleaned:
        return True, ""

    if not BIC_REGEX.match(cleaned):
        return False, f"Ungültiges BIC-Format: '{bic}'. Ein BIC muss 8 oder 11 Zeichen haben (z.B. BYLADEM1001)."

    return True, ""


def validate_creditor_id(creditor_id: str) -> Tuple[bool, str]:
    """
    Validate a SEPA Creditor Identifier (Gläubiger-ID).
    German format example: DE98ZZZ09999999999
    """
    cleaned = re.sub(r"[\s\-]", "", str(creditor_id).strip().upper())
    if not cleaned:
        return False, "Gläubiger-Identifikationsnummer darf nicht leer sein"

    if not CREDITOR_ID_REGEX.match(cleaned):
        return False, f"Ungültige Gläubiger-ID: '{creditor_id}'. Format z.B. DE98ZZZ09999999999"

    # Validate Modulo 97 check digit for creditor ID
    # Rearrange: from position 7 to end + country code (chars 0-2) + '00'
    # but ISO rules state creditor ID check digits are at index 2..4
    country = cleaned[:2]
    check_digits = cleaned[2:4]
    national_id = cleaned[7:]  # skipping business code at 4..7 (e.g. ZZZ)
    rearranged = national_id + country + check_digits

    digits = []
    for char in rearranged:
        if char.isdigit():
            digits.append(char)
        elif char.isalpha():
            digits.append(str(ord(char) - ord("A") + 10))
        else:
            return False, "Ungültiges Zeichen in Gläubiger-ID"

    num_str = "".join(digits)
    try:
        remainder = int(num_str) % 97
    except ValueError:
        return False, "Fehler bei Prüfsummenberechnung der Gläubiger-ID"

    if remainder != 1:
        return False, "Gläubiger-ID Prüfziffer ist falsch (Tippfehler)"

    return True, ""
