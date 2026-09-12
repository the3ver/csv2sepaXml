"""
Tests for IBAN, BIC, and Creditor ID validation.
"""

import unittest
from vereinseinzug.iban import (
    validate_iban,
    validate_bic,
    validate_creditor_id,
    clean_iban,
    clean_bic,
)


class TestIbanValidation(unittest.TestCase):
    def test_clean_iban(self):
        self.assertEqual(clean_iban(" de89 3704 0044 0532 0130 00 "), "DE89370400440532013000")
        self.assertEqual(clean_iban("DE-89-3704"), "DE893704")

    def test_valid_ibans(self):
        valid_ibans = [
            "DE89370400440532013000",
            "DE16120300000123456789",
            "DE44500105175407324931",
            "AT771932000000002345",
        ]
        for iban in valid_ibans:
            is_valid, msg = validate_iban(iban)
            self.assertTrue(is_valid, f"Expected {iban} to be valid, got error: {msg}")

    def test_invalid_checksum(self):
        # 1 digit changed
        is_valid, msg = validate_iban("DE89370400440532013001")
        self.assertFalse(is_valid)
        self.assertIn("Prüfsumme", msg)

    def test_invalid_length(self):
        # Too short for DE (needs 22)
        is_valid, msg = validate_iban("DE8937040044")
        self.assertFalse(is_valid)
        self.assertIn("22 Zeichen", msg)

    def test_empty_iban(self):
        is_valid, msg = validate_iban("")
        self.assertFalse(is_valid)

    def test_bic_validation(self):
        self.assertTrue(validate_bic("BYLADEM1001")[0])
        self.assertTrue(validate_bic("GENODED1PAU")[0])
        self.assertTrue(validate_bic("DEUTDEDD")[0])
        self.assertTrue(validate_bic("")[0])  # Optional
        self.assertTrue(validate_bic(None)[0])  # Optional

        self.assertFalse(validate_bic("INVALID_BIC_1234567")[0])
        self.assertFalse(validate_bic("1234")[0])

    def test_creditor_id(self):
        self.assertTrue(validate_creditor_id("DE98ZZZ09999999999")[0])
        self.assertFalse(validate_creditor_id("")[0])
        self.assertFalse(validate_creditor_id("INVALID")[0])


if __name__ == "__main__":
    unittest.main()
