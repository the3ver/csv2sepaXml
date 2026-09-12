"""
Configuration model and persistence for club (creditor) settings.
"""

import json
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from .iban import validate_iban, validate_bic, validate_creditor_id, clean_iban, clean_bic


@dataclass
class ClubConfig:
    creditor_name: str = ""
    creditor_id: str = ""
    creditor_iban: str = ""
    creditor_bic: Optional[str] = None
    collection_date: str = ""
    sequence_type: str = "RCUR"  # Default: RCUR (Folgelastschrift)
    default_remittance: str = "Mitgliedsbeitrag"
    batch_booking: bool = True  # BtchBookg (Sammelbuchung)

    def validate(self) -> List[str]:
        """Validate creditor configuration. Returns list of error messages."""
        errors: List[str] = []

        if not self.creditor_name.strip():
            errors.append("Vereinsname (Gläubigername) ist erforderlich.")
        elif len(self.creditor_name.strip()) > 70:
            errors.append("Vereinsname darf maximal 70 Zeichen lang sein.")

        if not self.creditor_id.strip():
            errors.append("Gläubiger-Identifikationsnummer (Creditor ID) ist erforderlich.")
        else:
            is_valid, msg = validate_creditor_id(self.creditor_id)
            if not is_valid:
                errors.append(f"Gläubiger-ID: {msg}")

        if not self.creditor_iban.strip():
            errors.append("Vereins-IBAN ist erforderlich.")
        else:
            is_valid, msg = validate_iban(self.creditor_iban)
            if not is_valid:
                errors.append(f"Vereins-IBAN: {msg}")

        if self.creditor_bic:
            is_valid, msg = validate_bic(self.creditor_bic)
            if not is_valid:
                errors.append(f"Vereins-BIC: {msg}")

        if self.sequence_type not in ("RCUR", "FRST", "OOFF", "FNAL"):
            errors.append(f"Ungültiger Sequenztyp: '{self.sequence_type}'. Erlaubt: RCUR, FRST, OOFF, FNAL")

        if not self.collection_date:
            # Set default collection date: 5 days from today
            self.collection_date = (date.today() + timedelta(days=5)).isoformat()
        else:
            try:
                dt = datetime.strptime(self.collection_date, "%Y-%m-%d").date()
                if dt < date.today():
                    errors.append(f"Fälligkeitsdatum ({self.collection_date}) liegt in der Vergangenheit.")
            except ValueError:
                errors.append(f"Fälligkeitsdatum ungültig ('{self.collection_date}'). Format muss JJJJ-MM-TT sein.")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClubConfig":
        return cls(
            creditor_name=data.get("creditor_name", "").strip(),
            creditor_id=re_clean_str(data.get("creditor_id", "")),
            creditor_iban=clean_iban(data.get("creditor_iban", "")),
            creditor_bic=clean_bic(data.get("creditor_bic")),
            collection_date=data.get("collection_date", "").strip(),
            sequence_type=data.get("sequence_type", "RCUR").strip().upper(),
            default_remittance=data.get("default_remittance", "Mitgliedsbeitrag").strip(),
            batch_booking=bool(data.get("batch_booking", True)),
        )

    def save_to_file(self, filepath: Path) -> None:
        """Save configuration as JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, filepath: Path) -> "ClubConfig":
        """Load configuration from JSON file."""
        with open(filepath, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return cls.from_dict(data)


def re_clean_str(val: Any) -> str:
    if not val:
        return ""
    return str(val).strip()


def get_app_dir() -> Path:
    """
    Get the directory containing the running executable or main script.
    When running as a PyInstaller bundle (.exe), sys.executable points to the .exe file.
    When running as a normal Python script, it resolves the main script directory.
    """
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    main_mod = sys.modules.get("__main__")
    if main_mod and getattr(main_mod, "__file__", None):
        return Path(main_mod.__file__).resolve().parent

    return Path.cwd()


def find_config_file(filename: str = "config.json") -> Optional[Path]:
    """
    Search for a configuration file:
    1. Directly next to the executable / application directory (get_app_dir)
    2. In the current working directory (Path.cwd())
    Returns Path if found, otherwise None.
    """
    # 1. Look directly next to the .exe / main script
    app_dir_path = get_app_dir() / filename
    if app_dir_path.is_file():
        return app_dir_path

    # 2. Look in current working directory
    cwd_path = Path.cwd() / filename
    if cwd_path.is_file():
        return cwd_path

    return None


def get_default_config_path(filename: str = "config.json") -> Path:
    """
    Return the path where config.json should be read from or written to:
    If an existing config.json is found (next to exe or in CWD), returns that path.
    Otherwise, defaults to placing it directly next to the executable / application directory.
    """
    existing = find_config_file(filename)
    if existing:
        return existing
    return get_app_dir() / filename

