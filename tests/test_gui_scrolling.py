import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import tkinter
except ImportError:  # pragma: no cover - python built without Tk
    tkinter = None

from cc_decrypter.discovery import DraftVideo


def _make_videos(count: int) -> list[DraftVideo]:
    return [
        DraftVideo(
            path=Path(f"/drafts/project{index}/video_{index:02d}.mp4"),
            relative=Path(f"project{index}/video_{index:02d}.mp4"),
            size=(index + 1) * 1024 * 1024,
            cryptor_type=1,
            created=1_700_000_000.0,
        )
        for index in range(count)
    ]


@unittest.skipIf(tkinter is None, "tkinter is unavailable")
class ListScrollingTests(unittest.TestCase):
    def setUp(self) -> None:
        from cc_decrypter import gui

        try:
            self.root = tkinter.Tk()
        except tkinter.TclError as exc:  # pragma: no cover - headless machine
            raise unittest.SkipTest(f"no display available: {exc}")
        self.addCleanup(self.root.destroy)
        # the list has to be on screen: scroll positions and hit testing are
        # measured against the real widget size.
        self.root.geometry("880x760")

        with patch.object(gui.DecrypterApp, "start_scan", lambda self: None):
            self.app = gui.DecrypterApp(self.root)
        self.canvas = self.app.list_canvas

    def _fill(self, count: int) -> None:
        # mirrors what the app does when a scan finishes
        self.app._results = _make_videos(count)
        self.app._scroll_list_to_top()
        self.app._draw_list()
        self.root.update()

    def test_wheel_event_on_the_window_scrolls_the_list(self) -> None:
        # Tk delivers a wheel event to the widget under the pointer, which is
        # usually not the list canvas, so the binding has to live on the window.
        self._fill(30)
        self.assertEqual(self.app._list_top(), 0.0)

        self.root.event_generate("<MouseWheel>", delta=-120, x=5, y=5)
        self.root.update()

        self.assertGreater(self.app._list_top(), 0.0)

    def test_wheel_event_on_the_list_scrolls_once(self) -> None:
        self._fill(30)

        self.canvas.event_generate("<MouseWheel>", delta=-120, x=300, y=200)
        self.root.update()
        self.assertAlmostEqual(self.app._list_top(), 20.0)

    def test_scrolling_stops_at_both_ends(self) -> None:
        self._fill(30)

        self.app._scroll_list(-5)
        self.assertEqual(self.app._list_top(), 0)

        self.app._scroll_list(500)
        self.assertAlmostEqual(
            self.app._list_top(), 30 * 48 - self.app._list_view_height()
        )

    def test_scrollbar_appears_only_when_rows_overflow(self) -> None:
        self._fill(4)
        self.assertIsNone(self.app._thumb_geometry())
        self.assertEqual(self.canvas.find_withtag("scrollbar"), ())

        self._fill(30)
        self.assertIsNotNone(self.app._thumb_geometry())
        self.assertNotEqual(self.canvas.find_withtag("scrollbar"), ())

    def test_thumb_travels_from_top_to_bottom(self) -> None:
        self._fill(30)
        _, top_of_thumb, _ = self.app._thumb_geometry()
        self.assertAlmostEqual(top_of_thumb, 3.0)

        self.app._scroll_list(500)
        track_top, bottom_thumb, thumb_height = self.app._thumb_geometry()
        track_height = self.app._list_view_height() - 2 * track_top
        self.assertAlmostEqual(bottom_thumb + thumb_height, track_top + track_height)

    def test_clicking_the_scrollbar_does_not_select_a_row(self) -> None:
        self._fill(30)

        self.canvas.event_generate("<Button-1>", x=636, y=200)
        self.root.update()

        self.assertEqual(self.app._selected, set())

    def test_page_and_end_keys_are_bound_to_the_window(self) -> None:
        bound = self.root.bind()

        for sequence in ("<Key-Prior>", "<Key-Next>", "<Key-Home>", "<Key-End>",
                         "<Key-Up>", "<Key-Down>"):
            self.assertIn(sequence, bound)

    def test_page_and_end_keys_scroll_the_list(self) -> None:
        self._fill(30)
        # Tk hands key events to the focus widget and drops them when the
        # toplevel holds no focus, which is how a CI desktop starts out.
        self.root.focus_force()
        self.root.update()

        self.root.event_generate("<Next>")
        self.root.update()
        self.assertGreater(self.app._list_top(), 0)

        self.root.event_generate("<End>")
        self.root.update()
        self.assertEqual(self.app._list_top(), self.app._max_scroll())

    def test_dragging_the_thumb_scrolls_the_list(self) -> None:
        self._fill(30)
        _, thumb_top, thumb_height = self.app._thumb_geometry()
        grab = int(thumb_top + thumb_height / 2)

        self.canvas.event_generate("<Button-1>", x=636, y=grab)
        self.canvas.event_generate("<B1-Motion>", x=636, y=grab + 50)
        self.root.update()
        dragged = self.app._list_top()

        self.canvas.event_generate("<ButtonRelease-1>", x=636, y=grab + 50)
        self.root.update()

        self.assertGreater(dragged, 0)
        self.assertLess(dragged, self.app._max_scroll())
        self.assertIsNone(self.app._thumb_drag)

    def test_clicking_the_track_below_the_thumb_pages_down(self) -> None:
        self._fill(30)
        _, thumb_top, thumb_height = self.app._thumb_geometry()

        self.canvas.event_generate("<Button-1>", x=636, y=int(thumb_top + thumb_height) + 20)
        self.root.update()

        self.assertGreater(self.app._list_top(), 0)
        self.assertEqual(self.app._selected, set())

    def test_clicking_a_row_still_selects_it(self) -> None:
        self._fill(30)

        self.canvas.event_generate("<Button-1>", x=200, y=20)
        self.root.update()

        self.assertEqual(self.app._selected, {0})


if __name__ == "__main__":
    unittest.main()
