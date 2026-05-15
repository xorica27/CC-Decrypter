from pathlib import Path
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "build.yml"
WINDOWS_INSTALLER = (
    Path(__file__).resolve().parents[1] / "installer" / "windows" / "cc-decrypter.iss"
)


class MacOSPackagingTests(unittest.TestCase):
    def test_macos_bundle_keeps_pyinstaller_binary_as_entrypoint(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("pyinstaller_name: CC-Decrypter", workflow)
        self.assertIn('--name "${{ matrix.pyinstaller_name }}"', workflow)
        self.assertIn('app_bundle="dist/CC Decrypter.app"', workflow)
        self.assertIn("Set :CFBundleDisplayName CC Decrypter", workflow)
        self.assertIn("CC-Decrypter-macOS-Apple-Silicon.dmg", workflow)
        self.assertIn("CC-Decrypter-macOS-Intel.dmg", workflow)
        self.assertIn("CC-Decrypter-Windows-x64-installer", workflow)
        self.assertIn("CFBundleExecutable", workflow)
        self.assertIn('file "$bundle_executable"', workflow)
        self.assertIn('"$bundle_executable" --smoke-test', workflow)
        self.assertIn("Install DMGForge", workflow)
        self.assertIn("scripts/generate_dmg_background.py", workflow)
        self.assertIn("dmgforge init", workflow)
        self.assertIn("dmgforge background", workflow)
        self.assertIn('dmgforge arrow "$project_path" --show --color "#111417"', workflow)
        self.assertIn("dmgforge export", workflow)

        windows_installer = WINDOWS_INSTALLER.read_text(encoding="utf-8")
        self.assertIn("CC-Decrypter-Windows-x64-Setup", windows_installer)


if __name__ == "__main__":
    unittest.main()
