"""
Tests for SEPA pain.008.001.08 XML generator and XSD validation.
"""

import unittest
from datetime import date, timedelta
from decimal import Decimal

from vereinseinzug.config import ClubConfig
from vereinseinzug.models import MemberPayment, sanitize_sepa_text
from vereinseinzug.generator import SepaPain008Generator


class TestSepaGenerator(unittest.TestCase):
    def setUp(self):
        self.config = ClubConfig(
            creditor_name="Turn- und Sportverein Musterstadt e.V.",
            creditor_id="DE98ZZZ09999999999",
            creditor_iban="DE89370400440532013000",
            creditor_bic="BYLADEM1001",
            collection_date=(date.today() + timedelta(days=10)).isoformat(),
            sequence_type="RCUR",
            default_remittance="Mitgliedsbeitrag 2026",
            batch_booking=True,
        )
        self.generator = SepaPain008Generator(self.config)

    def test_sanitize_sepa_text(self):
        # German umlauts replaced
        self.assertEqual(sanitize_sepa_text("Müller-Lüdenscheidt"), "Mueller-Luedenscheidt")
        self.assertEqual(sanitize_sepa_text("Groß & Partner"), "Gross + Partner")
        self.assertEqual(sanitize_sepa_text("Café René"), "Cafe Rene")
        # Length truncation
        self.assertEqual(len(sanitize_sepa_text("A" * 100, max_length=70)), 70)

    def test_xml_generation_and_xsd_validation(self):
        payments = [
            MemberPayment(
                name="Max Mustermann",
                iban="DE89370400440532013000",
                bic="BYLADEM1001",
                amount=Decimal("60.00"),
                mandate_id="M-00101",
                mandate_date="2022-03-15",
                remittance="Jahresbeitrag 2026",
                row_number=2,
            ),
            MemberPayment(
                name="Erika Musterfrau",
                iban="DE16120300000123456789",
                bic=None,
                amount=Decimal("45.50"),
                mandate_id="M-00102",
                mandate_date="2023-01-10",
                remittance="Mitgliedsbeitrag",
                row_number=3,
            ),
            MemberPayment(
                name="Hans Meier",
                iban="DE44500105175407324931",
                bic=None,
                amount=Decimal("120.00"),
                mandate_id="M-00103",
                mandate_date="2021-07-01",
                remittance="Familienbeitrag 2026",
                row_number=4,
            ),
        ]
        for p in payments:
            p.validate()
            self.assertTrue(p.is_valid, f"Payment {p.name} should be valid: {p.errors}")

        xml_output = self.generator.generate_xml(payments)

        # Check required tags and pain.008.001.08 namespace
        self.assertIn("urn:iso:std:iso:20022:tech:xsd:pain.008.001.08", xml_output)
        self.assertIn("<CstmrDrctDbtInitn>", xml_output)
        self.assertIn("<NbOfTxs>3</NbOfTxs>", xml_output)
        self.assertIn("<CtrlSum>225.50</CtrlSum>", xml_output)
        self.assertIn("<Cd>CORE</Cd>", xml_output)
        self.assertIn("<SeqTp>RCUR</SeqTp>", xml_output)
        self.assertIn("<BICFI>BYLADEM1001</BICFI>", xml_output)
        self.assertIn("<Id>NOTPROVIDED</Id>", xml_output)
        self.assertIn("<Id>DE98ZZZ09999999999</Id>", xml_output)

        # Strict validation against official XSD schema
        is_valid, errors = self.generator.validate_xml_schema(xml_output)
        self.assertTrue(is_valid, f"XSD schema errors: {errors}")


if __name__ == "__main__":
    unittest.main()
