import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# a windowless Qt platform so these run on any machine, CI included
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QMessageBox
except ImportError:  # pragma: no cover - PySide6 not installed
    QApplication = None

from cc_decrypter.discovery import DraftVideo

VIDEOS = [
    ("beta/clip_b.mp4", 300, 1_700_000_300.0, 1),
    ("alpha/clip_c.mp4", 100, 1_700_000_100.0, 1),
    ("gamma/clip_a.mp4", 200, 1_700_000_200.0, 1),
]


def make_videos(include_unsupported: bool = False) -> list[DraftVideo]:
    videos = [
        DraftVideo(
            path=Path("/drafts") / relative,
            relative=Path(relative),
            size=size,
            cryptor_type=cryptor,
            created=created,
        )
        for relative, size, created, cryptor in VIDEOS
    ]
    if include_unsupported:
        videos.append(
            DraftVideo(
                path=Path("/drafts/other/clip_x.mp4"),
                relative=Path("other/clip_x.mp4"),
                size=50,
                cryptor_type=2,
                created=1_700_000_000.0,
            )
        )
    return videos


@unittest.skipIf(QApplication is None, "PySide6 is unavailable")
class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        from cc_decrypter import gui

        self.gui = gui
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.drafts = self.tmp / "drafts"
        self.drafts.mkdir()

        self.saved_sort: list[tuple[str, bool]] = []
        self.saved_theme: list[str] = []
        self.saved_output: list[str] = []
        self.shown: list[tuple[str, str]] = []

        for target, replacement in (
            ("load_sort", lambda: None),
            ("load_theme", lambda: "light"),
            ("load_drafts_folder", lambda: None),
            ("load_output_folder", lambda: None),
            ("save_sort", lambda key, desc: self.saved_sort.append((key, desc))),
            ("save_theme", lambda theme: self.saved_theme.append(theme)),
            ("save_output_folder", lambda folder: self.saved_output.append(str(folder))),
            ("save_drafts_folder", lambda folder: None),
            ("resolve_drafts_folder", lambda saved: (self.drafts, None)),
            ("resolve_output_folder", lambda saved: self.tmp / "exports"),
        ):
            patcher = patch.object(gui, target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(
            QMessageBox, "information",
            lambda parent, title, message, *a, **k: self.shown.append((title, message)),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        with patch.object(gui.DecrypterWindow, "start_scan", lambda self: None):
            self.window = gui.DecrypterWindow()
        self.addCleanup(self.window.deleteLater)
        self.window.videos = make_videos()
        self.window._populate()

    def names(self) -> list[str]:
        return [
            self.window.list.item(row).data(self.gui.Qt.ItemDataRole.UserRole).path.name
            for row in range(self.window.list.count())
        ]

    def select(self, row: int) -> None:
        self.window.list.item(row).setSelected(True)

    # ------------------------------------------------------------- list

    def test_rows_carry_their_video_and_a_fixed_height(self) -> None:
        self.assertEqual(self.window.list.count(), 3)
        delegate = self.window.list.itemDelegate()
        self.assertEqual(delegate.sizeHint(None, None).height(), self.gui.ROW_HEIGHT)

    def test_selecting_rows_updates_the_count_and_the_button(self) -> None:
        self.assertFalse(self.window.cta.isEnabled())
        self.assertIn("0 of 3", self.window.counts.text())

        self.select(0)

        self.assertTrue(self.window.cta.isEnabled())
        self.assertEqual(self.window.cta.text(), "Decrypt 1 video")
        self.assertIn("1 of 3", self.window.counts.text())

        self.select(1)
        self.assertEqual(self.window.cta.text(), "Decrypt 2 videos")

    def test_the_button_is_dead_while_busy(self) -> None:
        self.select(0)
        self.window._set_busy(True)

        self.assertFalse(self.window.cta.isEnabled())
        self.assertEqual(self.window.cta.text(), "Working…")

    # ------------------------------------------------------------- sort

    def test_defaults_to_newest_first(self) -> None:
        self.assertEqual((self.window.sort_key, self.window.sort_descending), ("date", True))
        self.assertEqual(self.names(), ["clip_b.mp4", "clip_a.mp4", "clip_c.mp4"])

    def test_sorting_by_name_then_reversing(self) -> None:
        self.window.sort_buttons["name"].click()
        self.assertEqual(self.names(), ["clip_a.mp4", "clip_b.mp4", "clip_c.mp4"])

        self.window.sort_buttons["name"].click()
        self.assertEqual(self.names(), ["clip_c.mp4", "clip_b.mp4", "clip_a.mp4"])
        self.assertEqual(self.saved_sort, [("name", False), ("name", True)])

    def test_sorting_by_size_starts_with_the_largest(self) -> None:
        self.window.sort_buttons["size"].click()

        sizes = [
            self.window.list.item(row).data(self.gui.Qt.ItemDataRole.UserRole).size
            for row in range(self.window.list.count())
        ]
        self.assertEqual(sizes, [300, 200, 100])

    def test_selection_survives_a_re_sort(self) -> None:
        self.select(0)
        chosen = self.window.selected_videos()[0].path

        self.window.sort_buttons["name"].click()

        self.assertEqual([video.path for video in self.window.selected_videos()], [chosen])

    def test_the_active_sort_is_marked(self) -> None:
        self.assertIn("▾", self.window.sort_buttons["date"].text())

        self.window.sort_buttons["name"].click()

        self.assertIn("▴", self.window.sort_buttons["name"].text())
        self.assertNotIn("▾", self.window.sort_buttons["date"].text())

    # ------------------------------------------------------------ theme

    def test_switching_appearance_saves_and_applies_it(self) -> None:
        self.window.theme_buttons["dark"].click()

        self.assertEqual(self.window.theme, "dark")
        self.assertEqual(self.saved_theme, ["dark"])
        self.assertTrue(self.window.theme_buttons["dark"].isChecked())
        self.assertFalse(self.window.theme_buttons["light"].isChecked())

    def test_clicking_the_active_appearance_changes_nothing(self) -> None:
        self.window.theme_buttons["light"].click()

        self.assertEqual(self.saved_theme, [])

    # ---------------------------------------------------------- folders

    def test_changing_the_output_folder_saves_it(self) -> None:
        chosen = self.tmp / "elsewhere"
        chosen.mkdir()

        with patch.object(
            self.gui.QFileDialog, "getExistingDirectory", lambda *a, **k: str(chosen)
        ):
            self.window._on_change_output()

        self.assertEqual(self.window.output_dir, chosen)
        self.assertEqual(self.saved_output, [str(chosen)])
        self.assertIn(chosen.name, self.window.output_label.text())

    def test_cancelling_the_folder_picker_changes_nothing(self) -> None:
        before = self.window.output_dir

        with patch.object(self.gui.QFileDialog, "getExistingDirectory", lambda *a, **k: ""):
            self.window._on_change_output()

        self.assertEqual(self.window.output_dir, before)
        self.assertEqual(self.saved_output, [])

    def test_a_missing_saved_folder_is_reported(self) -> None:
        gone = self.tmp / "gone"

        self.window._report_missing_folder(gone)

        self.assertEqual(len(self.shown), 1)
        title, message = self.shown[0]
        self.assertIn("not found", title)
        self.assertIn(str(gone), message)
        self.assertIn(str(self.drafts), message)

    # ------------------------------------------------------------- scan

    def test_a_finished_scan_keeps_only_decryptable_videos(self) -> None:
        self.window._scan_finished(make_videos(include_unsupported=True), None)

        self.assertEqual(self.window.list.count(), 3)
        self.assertIn("Found 3 videos", self.window.status.text())
        self.assertTrue(any("unsupported" in line for line in self.window.log_lines))

    def test_a_failed_scan_says_so(self) -> None:
        self.window._scan_finished(None, OSError("nope"))

        self.assertIn("went wrong", self.window.status.text())
        self.assertTrue(any("ERROR while searching" in line for line in self.window.log_lines))

    def test_an_empty_folder_says_so(self) -> None:
        self.window._scan_finished([], None)

        self.assertEqual(self.window.list.count(), 0)
        self.assertIn("No protected videos", self.window.status.text())
        self.assertIn("Nothing to decrypt", self.window.counts.text())

    # -------------------------------------------------------------- log

    def test_the_log_window_shows_what_was_written(self) -> None:
        self.window.write_log("first line")
        self.window.write_log("second line")
        self.app.processEvents()

        self.window.show_log()

        self.assertIn("first line", self.window.log_window.text.toPlainText())
        self.assertIn("second line", self.window.log_window.text.toPlainText())


if __name__ == "__main__":
    unittest.main()
