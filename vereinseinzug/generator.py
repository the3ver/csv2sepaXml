"""
SEPA Direct Debit (pain.008.001.08) XML Generator with XSD Schema Validation.
"""

import os
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

from .config import ClubConfig
from .models import MemberPayment, sanitize_sepa_text

PAIN_008_001_08_NAMESPACE = "urn:iso:std:iso:20022:tech:xsd:pain.008.001.08"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"


def get_schema_path() -> Path:
    """Return the path to the bundled pain.008.001.08.xsd schema file."""
    import sys
    candidates = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "schema" / "pain.008.001.08.xsd")
        candidates.append(Path(sys._MEIPASS) / "pain.008.001.08.xsd")

    pkg_dir = Path(__file__).parent
    candidates.extend([
        pkg_dir.parent / "schema" / "pain.008.001.08.xsd",
        pkg_dir / "schema" / "pain.008.001.08.xsd",
    ])
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError("pain.008.001.08.xsd schema file not found.")


def indent_xml(elem: ET.Element, level: int = 0) -> None:
    """Add pretty indentation to XML ElementTree."""
    indent = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent
        for subelem in elem:
            indent_xml(subelem, level + 1)
        if not subelem.tail or not subelem.tail.strip():
            subelem.tail = indent
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent


class SepaPain008Generator:
    """
    Builds and validates ISO 20022 pain.008.001.08 XML documents.
    """

    def __init__(self, config: ClubConfig):
        self.config = config

    def generate_xml(
        self,
        payments: List[MemberPayment],
        message_id: Optional[str] = None,
        payment_info_id: Optional[str] = None,
    ) -> str:
        """
        Generate a pain.008.001.08 compliant XML string.
        Only payments where is_valid == True will be included.
        """
        valid_payments = [p for p in payments if p.is_valid]
        if not valid_payments:
            raise ValueError("Keine gültigen Zahlungssätze vorhanden.")

        config_errors = self.config.validate()
        if config_errors:
            raise ValueError(f"Ungültige Vereinsdaten: {'; '.join(config_errors)}")

        now = datetime.now()
        timestamp_str = now.strftime("%Y-%m-%dT%H:%M:%S")
        date_short = now.strftime("%Y%m%d%H%M%S")

        # Generate unique IDs if not provided
        if not message_id:
            message_id = sanitize_sepa_text(f"MSG-{date_short}-{uuid.uuid4().hex[:6]}", 35)
        else:
            message_id = sanitize_sepa_text(message_id, 35)

        if not payment_info_id:
            payment_info_id = sanitize_sepa_text(f"PMT-{date_short}-1", 35)
        else:
            payment_info_id = sanitize_sepa_text(payment_info_id, 35)

        total_amount = sum((p.amount for p in valid_payments), Decimal("0.00"))
        nb_of_txs = len(valid_payments)
        ctrl_sum_str = f"{total_amount:.2f}"

        # Root Document element
        ET.register_namespace("", PAIN_008_001_08_NAMESPACE)
        ET.register_namespace("xsi", XSI_NAMESPACE)

        doc = ET.Element(f"{{{PAIN_008_001_08_NAMESPACE}}}Document", {
            f"{{{XSI_NAMESPACE}}}schemaLocation": f"{PAIN_008_001_08_NAMESPACE} pain.008.001.08.xsd"
        })

        initiation = ET.SubElement(doc, "CstmrDrctDbtInitn")

        # 1. Group Header (GrpHdr)
        grp_hdr = ET.SubElement(initiation, "GrpHdr")
        ET.SubElement(grp_hdr, "MsgId").text = message_id
        ET.SubElement(grp_hdr, "CreDtTm").text = timestamp_str
        ET.SubElement(grp_hdr, "NbOfTxs").text = str(nb_of_txs)
        ET.SubElement(grp_hdr, "CtrlSum").text = ctrl_sum_str

        initg_pty = ET.SubElement(grp_hdr, "InitgPty")
        ET.SubElement(initg_pty, "Nm").text = sanitize_sepa_text(self.config.creditor_name, 70)

        # 2. Payment Information (PmtInf)
        pmt_inf = ET.SubElement(initiation, "PmtInf")
        ET.SubElement(pmt_inf, "PmtInfId").text = payment_info_id
        ET.SubElement(pmt_inf, "PmtMtd").text = "DD"  # Direct Debit
        ET.SubElement(pmt_inf, "BtchBookg").text = "true" if self.config.batch_booking else "false"
        ET.SubElement(pmt_inf, "NbOfTxs").text = str(nb_of_txs)
        ET.SubElement(pmt_inf, "CtrlSum").text = ctrl_sum_str

        # Payment Type Info
        pmt_tp_inf = ET.SubElement(pmt_inf, "PmtTpInf")
        svc_lvl = ET.SubElement(pmt_tp_inf, "SvcLvl")
        ET.SubElement(svc_lvl, "Cd").text = "SEPA"
        lcl_instrm = ET.SubElement(pmt_tp_inf, "LclInstrm")
        ET.SubElement(lcl_instrm, "Cd").text = "CORE"  # Standard SEPA Core Direct Debit
        ET.SubElement(pmt_tp_inf, "SeqTp").text = self.config.sequence_type

        # Collection Date
        ET.SubElement(pmt_inf, "ReqdColltnDt").text = self.config.collection_date

        # Creditor Info
        cdtr = ET.SubElement(pmt_inf, "Cdtr")
        ET.SubElement(cdtr, "Nm").text = sanitize_sepa_text(self.config.creditor_name, 70)

        cdtr_acct = ET.SubElement(pmt_inf, "CdtrAcct")
        cdtr_acct_id = ET.SubElement(cdtr_acct, "Id")
        ET.SubElement(cdtr_acct_id, "IBAN").text = self.config.creditor_iban

        # Creditor Agent (BICFI in pain.008.001.08)
        cdtr_agt = ET.SubElement(pmt_inf, "CdtrAgt")
        cdtr_fin_instn = ET.SubElement(cdtr_agt, "FinInstnId")
        if self.config.creditor_bic:
            ET.SubElement(cdtr_fin_instn, "BICFI").text = self.config.creditor_bic
        else:
            othr = ET.SubElement(cdtr_fin_instn, "Othr")
            ET.SubElement(othr, "Id").text = "NOTPROVIDED"

        # Charge Bearer
        ET.SubElement(pmt_inf, "ChrgBr").text = "SLEV"

        # Creditor Scheme Identification (Gläubiger-ID)
        cdtr_schme = ET.SubElement(pmt_inf, "CdtrSchmeId")
        schme_id = ET.SubElement(cdtr_schme, "Id")
        prvt_id = ET.SubElement(schme_id, "PrvtId")
        othr_id = ET.SubElement(prvt_id, "Othr")
        ET.SubElement(othr_id, "Id").text = self.config.creditor_id
        schme_nm = ET.SubElement(othr_id, "SchmeNm")
        ET.SubElement(schme_nm, "Prtry").text = "SEPA"

        # 3. Direct Debit Transaction Information (DrctDbtTxInf)
        for payment in valid_payments:
            tx_inf = ET.SubElement(pmt_inf, "DrctDbtTxInf")

            # Payment Identification
            pmt_id = ET.SubElement(tx_inf, "PmtId")
            ET.SubElement(pmt_id, "EndToEndId").text = payment.end_to_end_id

            # Instructed Amount
            instd_amt = ET.SubElement(tx_inf, "InstdAmt", {"Ccy": "EUR"})
            instd_amt.text = f"{payment.amount:.2f}"

            # Direct Debit Transaction -> Mandate Related Information
            drct_dbt_tx = ET.SubElement(tx_inf, "DrctDbtTx")
            mndt_info = ET.SubElement(drct_dbt_tx, "MndtRltdInf")
            ET.SubElement(mndt_info, "MndtId").text = payment.mandate_id
            ET.SubElement(mndt_info, "DtOfSgntr").text = payment.mandate_date

            # Debtor Agent (Debtor BIC or NOTPROVIDED)
            dbtr_agt = ET.SubElement(tx_inf, "DbtrAgt")
            dbtr_fin_instn = ET.SubElement(dbtr_agt, "FinInstnId")
            if payment.bic:
                ET.SubElement(dbtr_fin_instn, "BICFI").text = payment.bic
            else:
                dbtr_othr = ET.SubElement(dbtr_fin_instn, "Othr")
                ET.SubElement(dbtr_othr, "Id").text = "NOTPROVIDED"

            # Debtor (Member Name)
            dbtr = ET.SubElement(tx_inf, "Dbtr")
            ET.SubElement(dbtr, "Nm").text = sanitize_sepa_text(payment.name, 70)

            # Debtor Account (Member IBAN)
            dbtr_acct = ET.SubElement(tx_inf, "DbtrAcct")
            dbtr_acct_id = ET.SubElement(dbtr_acct, "Id")
            ET.SubElement(dbtr_acct_id, "IBAN").text = payment.iban

            # Remittance Information
            remittance_text = payment.remittance or self.config.default_remittance
            if remittance_text:
                rmt_inf = ET.SubElement(tx_inf, "RmtInf")
                ET.SubElement(rmt_inf, "Ustrd").text = sanitize_sepa_text(remittance_text, 140)

        # Indent and convert to string
        indent_xml(doc)
        xml_bytes = ET.tostring(doc, encoding="utf-8", xml_declaration=True)
        return xml_bytes.decode("utf-8")

    def validate_xml_schema(self, xml_content: str) -> Tuple[bool, List[str]]:
        """
        Validate XML against pain.008.001.08.xsd using xmlschema.
        Returns (is_valid, error_list).
        """
        try:
            import xmlschema
            schema_file = get_schema_path()
            schema = xmlschema.XMLSchema(str(schema_file))
            errors = list(schema.iter_errors(xml_content))
            if not errors:
                return True, []
            return False, [str(err.message) for err in errors]
        except Exception as e:
            return False, [f"Schemavalidierungsfehler: {str(e)}"]
