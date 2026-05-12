from pathlib import Path
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "build.yml"


class MacOSPackagingTests(unittest.TestCase):
    def test_macos_bundle_keeps_pyinstaller_binary_as_entrypoint(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertNotIn("CC Video Repair-bin", workflow)
        self.assertNotIn('cat > "${app_macos}/CC Video Repair"', workflow)
        self.assertIn("CFBundleExecutable", workflow)
        self.assertIn('file "$bundle_executable"', workflow)


if __name__ == "__main__":
    unittest.main()
