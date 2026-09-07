import re
import unittest
from pathlib import Path
from unittest.mock import patch

import cc_decrypter
from cc_decrypter import app

ROOT = Path(__file__).resolve().parents[1]


class AppStartupTests(unittest.TestCase):
    def test_smoke_test_mode_runs_without_opening_gui(self) -> None:
        calls = []

        with patch.object(app, "_run_smoke_test", side_effect=lambda: calls.append("smoke")):
            app.main(["--smoke-test"])

        self.assertEqual(calls, ["smoke"])


class VersionTests(unittest.TestCase):
    """The Windows installer version was once left behind for three releases."""

    def _declared(self, path: str, pattern: str) -> str:
        match = re.search(pattern, (ROOT / path).read_text(encoding="utf-8"))
        self.assertIsNotNone(match, f"no version found in {path}")
        return match.group(1)

    def test_every_file_declares_the_same_version(self) -> None:
        package = cc_decrypter.__version__

        self.assertEqual(self._declared("pyproject.toml", r'version = "([^"]+)"'), package)
        self.assertEqual(
            self._declared("installer/windows/cc-decrypter.iss", r'MyAppVersion "([^"]+)"'),
            package,
        )

    def test_the_changelog_documents_this_version(self) -> None:
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertIn(f"## {cc_decrypter.__version__} — ", changelog)


if __name__ == "__main__":
    unittest.main()
