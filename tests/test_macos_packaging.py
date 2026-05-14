from pathlib import Path
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "build.yml"
WINDOWS_INSTALLER = (
    Path(__file__).resolve().parents[1] / "installer" / "windows" / "cc-decrypter.iss"
)


class MacOSPackagingTests(unittest.TestCase):
    def test_macos_bundle_keeps_pyinstaller_binary_as_entrypoint(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn('--name "CC Decrypter"', workflow)
        self.assertIn("CC-Decrypter-macOS-Apple-Silicon.dmg", workflow)
        self.assertIn("CC-Decrypter-macOS-Intel.dmg", workflow)
        self.assertIn("CC-Decrypter-Windows-x64-installer", workflow)
        self.assertIn("CFBundleExecutable", workflow)
        self.assertIn('file "$bundle_executable"', workflow)
        self.assertIn('"$bundle_executable" --smoke-test', workflow)

        windows_installer = WINDOWS_INSTALLER.read_text(encoding="utf-8")
        self.assertIn("CC-Decrypter-Windows-x64-Setup", windows_installer)


if __name__ == "__main__":
    unittest.main()
