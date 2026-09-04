import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cc_decrypter import settings


class SettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "CC Decrypter" / "settings.json"
        patcher = patch.object(settings, "settings_path", return_value=self.path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_load_missing_file_returns_none(self) -> None:
        self.assertIsNone(settings.load_theme())

    def test_save_and_load_roundtrip(self) -> None:
        settings.save_theme("dark")

        self.assertEqual(settings.load_theme(), "dark")

        settings.save_theme("light")

        self.assertEqual(settings.load_theme(), "light")

    def test_saved_file_contains_json_theme(self) -> None:
        import json

        settings.save_theme("light")

        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), {"theme": "light"})

    def test_load_invalid_theme_returns_none(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text('{"theme": "purple"}', encoding="utf-8")

        self.assertIsNone(settings.load_theme())

    def test_load_corrupt_file_returns_none(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text("not json at all", encoding="utf-8")

        self.assertIsNone(settings.load_theme())

    def test_save_rejects_unknown_theme(self) -> None:
        with self.assertRaises(ValueError):
            settings.save_theme("purple")

    def test_save_swallows_unwritable_location(self) -> None:
        blocker = self.path.parent
        blocker.mkdir(parents=True)
        blocker_file = blocker / "as-file"
        blocker_file.write_bytes(b"")
        with patch.object(settings, "settings_path", return_value=blocker_file / "s.json"):
            settings.save_theme("dark")  # must not raise

    def test_detect_system_theme_returns_known_theme(self) -> None:
        self.assertIn(settings.detect_system_theme(), settings.THEMES)

    def test_drafts_folder_roundtrip(self) -> None:
        self.assertIsNone(settings.load_drafts_folder())

        settings.save_drafts_folder(Path("/tmp/some folder"))

        self.assertEqual(settings.load_drafts_folder(), Path("/tmp/some folder"))

    def test_theme_and_drafts_folder_settings_merge(self) -> None:
        settings.save_theme("dark")
        settings.save_drafts_folder("/x/y")

        self.assertEqual(settings.load_theme(), "dark")
        self.assertEqual(settings.load_drafts_folder(), Path("/x/y"))

    def test_load_drafts_folder_ignores_non_string_value(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text('{"drafts_folder": 123}', encoding="utf-8")

        self.assertIsNone(settings.load_drafts_folder())


if __name__ == "__main__":
    unittest.main()
