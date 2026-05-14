import unittest
from unittest.mock import patch

from cc_decrypter import app


class AppStartupTests(unittest.TestCase):
    def test_smoke_test_mode_runs_without_opening_gui(self) -> None:
        calls = []

        with patch.object(app, "_run_smoke_test", side_effect=lambda: calls.append("smoke")):
            app.main(["--smoke-test"])

        self.assertEqual(calls, ["smoke"])


if __name__ == "__main__":
    unittest.main()
