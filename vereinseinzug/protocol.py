"""
Generation of formal SEPA direct debit audit protocols for club records / Kassenprüfung.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional

from .config import ClubConfig
from .models import MemberPayment
from .logger import mask_iban


def generate_audit_protocol(
    config: ClubConfig,
    payments: List[MemberPayment],
    stats: Dict[str, Any],
    xml_filename: Optional[str] = None,
) -> str:
    """
    Generate a formal audit report for club treasurers and auditors.
    """
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    valid_payments = [p for p in payments if p.is_valid]
    invalid_payments = [p for p in payments if not p.is_valid]

    total_amount = sum((p.amount for p in valid_payments), Decimal("0.00"))
    total_amount_str = f"{total_amount:.2f} €".replace(".", ",")

    lines = []
    lines.append("=" * 80)
    lines.append("                    SEPA-EINZUGSPROTOKOLL (pain.008.001.08)")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Erstellt am:           {now_str}")
    lines.append(f"Geplantes Einzugsdatum:{config.collection_date}")
    lines.append(f"Gläubiger (Verein):    {config.creditor_name}")
    lines.append(f"Gläubiger-ID:          {config.creditor_id}")
    lines.append(f"Vereins-IBAN:          {mask_iban(config.creditor_iban)}")
    if config.creditor_bic:
        lines.append(f"Vereins-BIC:           {config.creditor_bic}")
    lines.append(f"Sequenztyp:            {config.sequence_type} ({'Folgelastschrift' if config.sequence_type == 'RCUR' else config.sequence_type})")
    lines.append(f"Sammelbuchung:         {'Ja (1 Sammelposten auf Kontoauszug)' if config.batch_booking else 'Nein (Einzelbuchungen)'}")
    if xml_filename:
        lines.append(f"Zugehörige XML-Datei:  {xml_filename}")
    lines.append("")
    lines.append("-" * 80)
    lines.append("ZUSAMMENFASSUNG")
    lines.append("-" * 80)
    lines.append(f"Gelesene Datensätze:      {len(payments)}")
    lines.append(f"Erfolgreich eingezogen:   {len(valid_payments)}")
    lines.append(f"Abgewiesen / Fehlerhaft:  {len(invalid_payments)}")
    lines.append(f"Gesamteinzugssumme:       {total_amount_str}")
    lines.append("")
    lines.append("-" * 80)
    lines.append(f"EINGEZOGENE POSTEN ({len(valid_payments)})")
    lines.append("-" * 80)
    lines.append(f"{'Nr.':<4} | {'Name des Mitglieds':<28} | {'IBAN (maskiert)':<24} | {'Mandat':<10} | {'Betrag':>9}")
    lines.append("-" * 80)

    for idx, p in enumerate(valid_payments, start=1):
        name_short = p.name[:28]
        iban_m = mask_iban(p.iban)
        amt_str = f"{p.amount:.2f} €".replace(".", ",")
        m_id = p.mandate_id[:10]
        lines.append(f"{idx:<4} | {name_short:<28} | {iban_m:<24} | {m_id:<10} | {amt_str:>9}")

    lines.append("-" * 80)
    lines.append(f"{'SUMME:':<70} {total_amount_str:>9}")
    lines.append("")

    lines.append("-" * 80)
    lines.append(f"ABGEWIESENE / FEHLERHAFTE POSTEN ({len(invalid_payments)})")
    lines.append("-" * 80)

    if not invalid_payments:
        lines.append("Keine fehlerhaften Datensätze. Alle Datensätze wurden erfolgreich übernommen.")
    else:
        for idx, p in enumerate(invalid_payments, start=1):
            name_short = p.name[:28]
            lines.append(f"[Fehler #{idx}] Zeile {p.row_number} - {name_short}")
            for err in p.errors:
                lines.append(f"  - Ursache: {err}")
            lines.append("")

    lines.append("")
    lines.append("=" * 80)
    lines.append("HINWEIS FÜR DIE KASSENPRÜFUNG:")
    lines.append("Dieses Dokument dient als Nachweis für die ordnungsgemäße Erstellung der")
    lines.append("SEPA-Basislastschrift. Alle Mandate müssen dem Verein unterschrieben vorliegen.")
    lines.append("=" * 80)
    lines.append("")

    return "\n".join(lines)
