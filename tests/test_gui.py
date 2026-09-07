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
        self.exports = self.tmp / "exports"
        self.exports.mkdir()
        self.saved_geometry: list[tuple] = []

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
            ("resolve_output_folder", lambda saved: self.exports),
            ("load_window_geometry", lambda: None),
            ("save_window_geometry", lambda *a: self.saved_geometry.append(a)),
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


    # -------------------------------------------------------- decrypting

    def test_progress_and_cancel_appear_only_while_working(self) -> None:
        self.assertFalse(self.window.progress.isVisibleTo(self.window))
        self.assertFalse(self.window.cancel_button.isVisibleTo(self.window))

        self.window._batch_progressed(2, 5, "clip_b.mp4")

        self.assertEqual(self.window.progress.value(), 2)
        self.assertEqual(self.window.progress.maximum(), 5)
        self.assertIn("3 of 5", self.window.status.text())
        self.assertIn("clip_b.mp4", self.window.status.text())

    def test_cancelling_asks_the_worker_to_stop(self) -> None:
        self.window._request_cancel()

        self.assertTrue(self.window.cancel_requested.is_set())
        self.assertFalse(self.window.cancel_button.isEnabled())
        self.assertIn("Finishing the current video", self.window.status.text())

    def test_a_cancelled_run_reports_what_it_managed(self) -> None:
        self.window._batch_finished(2, 0, 5, True)

        self.assertIn("Stopped: 2 of 5", self.window.status.text())
        self.assertFalse(self.window.progress.isVisibleTo(self.window))

    def test_the_worker_stops_when_cancelled(self) -> None:
        self.window.cancel_requested.set()
        finished: list[tuple] = []
        self.window.batch_done.connect(lambda *args: finished.append(args))

        self.window._batch_worker(make_videos(), self.exports)
        self.app.processEvents()

        self.assertEqual(finished, [(0, 0, 3, True)])

    # ---------------------------------------------------- already exported

    def test_videos_already_in_the_output_folder_are_marked(self) -> None:
        from cc_decrypter.discovery import export_base_name

        (self.exports / f"{export_base_name(self.window.videos[0])}.mp4").write_bytes(b"x")
        self.window._populate()

        marks = [
            bool(self.window.list.item(row).data(self.gui.EXPORTED_ROLE))
            for row in range(self.window.list.count())
        ]
        self.assertEqual(marks.count(True), 1)

    def test_picking_an_exported_video_offers_to_skip_it(self) -> None:
        from cc_decrypter.discovery import export_base_name

        for video in self.window.videos:
            (self.exports / f"{export_base_name(video)}.mp4").write_bytes(b"x")
        self.window._populate()
        self.window.list.selectAll()
        started: list = []
        self.window._batch_worker = lambda *args: started.append(args)

        with patch.object(
            self.gui.QMessageBox, "question",
            lambda *a, **k: self.gui.QMessageBox.StandardButton.Yes,
        ):
            self.window.start_batch()

        self.assertEqual(started, [])
        self.assertIn("already exported", self.window.status.text())

    # --------------------------------------------------------- reveal

    def test_the_output_path_opens_the_folder(self) -> None:
        opened: list = []

        with patch.object(self.gui, "reveal", opened.append):
            self.window._reveal_output()

        self.assertEqual(opened, [self.exports])

    def test_revealing_a_folder_that_does_not_exist_yet_explains_itself(self) -> None:
        self.window.output_dir = self.tmp / "not yet"
        opened: list = []

        with patch.object(self.gui, "reveal", opened.append):
            self.window._reveal_output()

        self.assertEqual(opened, [])
        self.assertIn("appears when the first video", self.window.status.text())

    # -------------------------------------------------------- menus etc.

    def test_the_menu_offers_the_actions_with_shortcuts(self) -> None:
        actions = self.window.actions_by_name

        for name in ("Rescan", "Decrypt Selected", "Select All", "View Log",
                     "About CC Decrypter", "Open Output Folder"):
            self.assertIn(name, actions)
        self.assertEqual(actions["Rescan"].shortcut().toString(), "Ctrl+R")
        self.assertEqual(actions["View Log"].shortcut().toString(), "Ctrl+L")

    def test_the_window_size_is_saved_on_close(self) -> None:
        self.window.resize(820, 700)
        self.window.close()

        self.assertEqual(len(self.saved_geometry), 1)
        _, _, width, height = self.saved_geometry[0]
        self.assertEqual((width, height), (820, 700))

    def test_a_saved_size_is_restored(self) -> None:
        with patch.object(self.gui, "load_window_geometry", lambda: (0, 0, 760, 640)), \
                patch.object(self.gui.DecrypterWindow, "start_scan", lambda self: None):
            window = self.gui.DecrypterWindow()
        self.addCleanup(window.deleteLater)

        self.assertEqual((window.width(), window.height()), (760, 640))

    # ------------------------------------------------------- update check

    def test_version_comparison(self) -> None:
        self.assertGreater(self.gui.version_tuple("v0.3.1"), self.gui.version_tuple("0.3.0"))
        self.assertGreater(self.gui.version_tuple("0.10.0"), self.gui.version_tuple("0.9.9"))
        self.assertEqual(self.gui.version_tuple("0.3.0"), self.gui.version_tuple("v0.3.0"))

    def test_the_update_check_reports_each_outcome(self) -> None:
        import cc_decrypter

        self.window.show_about()
        about = self.window.about_dialog

        about._show_update("99.0.0", "")
        self.assertIn("99.0.0 is available", about.update_status.text())

        about._show_update(cc_decrypter.__version__, "")
        self.assertIn("up to date", about.update_status.text())

        about._show_update("", "no network")
        self.assertIn("no network", about.update_status.text())

    # ------------------------------------------------------------ about

    def test_about_reports_the_running_version(self) -> None:
        import cc_decrypter

        self.window.show_about()

        details = self.window.about_dialog.details.toPlainText()
        self.assertIn(cc_decrypter.__version__, details)
        self.assertIn("Qt ", details)
        self.assertIn("Settings:", details)

    def test_about_opens_once_and_is_reachable_from_the_footer(self) -> None:
        self.window.show_about()
        first = self.window.about_dialog

        self.window.show_about()

        self.assertIs(self.window.about_dialog, first)
        self.assertTrue(
            any(
                button.text().startswith("About")
                for button in self.window.findChildren(self.gui.QToolButton)
            )
        )

    def test_the_version_is_logged_for_bug_reports(self) -> None:
        import cc_decrypter

        self.app.processEvents()

        self.assertTrue(
            any(cc_decrypter.__version__ in line for line in self.window.log_lines)
        )


if __name__ == "__main__":
    unittest.main()
