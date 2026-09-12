"""
Tests for CSV parser and flexible column mapping.
"""

import unittest
from decimal import Decimal
from vereinseinzug.parser import parse_csv_content, parse_amount, detect_delimiter


class TestParser(unittest.TestCase):
    def test_detect_delimiter(self):
        self.assertEqual(detect_delimiter("a;b;c\n1;2;3"), ";")
        self.assertEqual(detect_delimiter("a,b,c\n1,2,3"), ",")
        self.assertEqual(detect_delimiter("a\tb\tc\n1\t2\t3"), "\t")

    def test_parse_amount(self):
        self.assertEqual(parse_amount("50,00"), Decimal("50.00"))
        self.assertEqual(parse_amount("50,00 €"), Decimal("50.00"))
        self.assertEqual(parse_amount("1.250,50"), Decimal("1250.50"))
        self.assertEqual(parse_amount("45.50"), Decimal("45.50"))
        self.assertEqual(parse_amount(""), Decimal("0.00"))

    def test_parse_csv_semicolon(self):
        csv_data = """Name;IBAN;BIC;Betrag;Mandatsreferenz;Mandatsdatum;Verwendungszweck
Max Mustermann;DE89370400440532013000;BYLADEM1001;60,00;M-001;2022-03-15;Beitrag 2026
Erika Musterfrau;DE16120300000123456789;;45,50;M-002;15.01.2023;Beitrag 2026"""

        payments, stats = parse_csv_content(csv_data)
        self.assertEqual(stats["total_records"], 2)
        self.assertEqual(stats["valid_records"], 2)
        self.assertEqual(stats["total_amount"], 105.50)
        self.assertEqual(payments[0].name, "Max Mustermann")
        self.assertEqual(payments[0].mandate_date, "2022-03-15")
        # Check date parsed from DD.MM.YYYY
        self.assertEqual(payments[1].mandate_date, "2023-01-15")

    def test_parse_csv_separate_first_last_name(self):
        csv_data = """Vorname,Nachname,IBAN,Beitrag,Mandatsnummer,Datum
Anna,Schmidt,DE82100777770346822303,75.00,M-100,2021-05-10"""

        payments, stats = parse_csv_content(csv_data)
        self.assertEqual(stats["total_records"], 1)
        self.assertEqual(payments[0].name, "Anna Schmidt")
        self.assertEqual(payments[0].amount, Decimal("75.00"))
        self.assertTrue(payments[0].is_valid)

    def test_parse_csv_missing_columns(self):
        csv_data = """Telefon;Adresse\n1234;Testweg 1"""
        payments, stats = parse_csv_content(csv_data)
        self.assertIn("error", stats)


if __name__ == "__main__":
    unittest.main()
