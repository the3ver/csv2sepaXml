"""
Unit tests for ClubConfig and config path resolution.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vereinseinzug.config import (
    ClubConfig,
    find_config_file,
    get_default_config_path,
    get_app_dir,
)


class TestConfig(unittest.TestCase):
    def test_club_config_validation(self):
        cfg = ClubConfig(
            creditor_name="Testverein e.V.",
            creditor_id="DE98ZZZ09999999999",
            creditor_iban="DE89370400440532013000",
            sequence_type="RCUR",
        )
        errors = cfg.validate()
        self.assertEqual(errors, [])

    def test_find_config_file_next_to_app(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app_dir = Path(tmpdir)
            cfg_file = app_dir / "config.json"
            cfg_file.write_text('{"creditor_name": "AppDir Club"}', encoding="utf-8")

            with patch("vereinseinzug.config.get_app_dir", return_value=app_dir):
                found = find_config_file("config.json")
                self.assertIsNotNone(found)
                self.assertEqual(found.resolve(), cfg_file.resolve())

    def test_find_config_file_in_cwd(self):
        with tempfile.TemporaryDirectory() as tmp_app, tempfile.TemporaryDirectory() as tmp_cwd:
            app_dir = Path(tmp_app)
            cwd_dir = Path(tmp_cwd)
            cfg_file = cwd_dir / "config.json"
            cfg_file.write_text('{"creditor_name": "CWD Club"}', encoding="utf-8")

            with patch("vereinseinzug.config.get_app_dir", return_value=app_dir):
                with patch("pathlib.Path.cwd", return_value=cwd_dir):
                    found = find_config_file("config.json")
                    self.assertIsNotNone(found)
                    self.assertEqual(found.resolve(), cfg_file.resolve())

    def test_find_config_file_none(self):
        with tempfile.TemporaryDirectory() as tmp_app, tempfile.TemporaryDirectory() as tmp_cwd:
            with patch("vereinseinzug.config.get_app_dir", return_value=Path(tmp_app)):
                with patch("pathlib.Path.cwd", return_value=Path(tmp_cwd)):
                    found = find_config_file("config.json")
                    self.assertIsNone(found)

    def test_get_default_config_path_prefers_app_dir(self):
        with tempfile.TemporaryDirectory() as tmp_app, tempfile.TemporaryDirectory() as tmp_cwd:
            app_dir = Path(tmp_app)
            cwd_dir = Path(tmp_cwd)
            with patch("vereinseinzug.config.get_app_dir", return_value=app_dir):
                with patch("pathlib.Path.cwd", return_value=cwd_dir):
                    default_path = get_default_config_path("config.json")
                    self.assertEqual(default_path.resolve(), (app_dir / "config.json").resolve())

    def test_load_config_with_utf8_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.json"
            # Write with explicit UTF-8 BOM (\xef\xbb\xbf)
            bom_content = b'\xef\xbb\xbf{"creditor_name": "BOM Club", "creditor_id": "DE98ZZZ09999999999", "creditor_iban": "DE89370400440532013000"}'
            cfg_path.write_bytes(bom_content)
            loaded = ClubConfig.load_from_file(cfg_path)
            self.assertEqual(loaded.creditor_name, "BOM Club")


if __name__ == "__main__":
    unittest.main()
