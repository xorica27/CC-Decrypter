import unittest
from unittest.mock import patch

try:
    import tkinter
except ImportError:  # pragma: no cover - python built without Tk
    tkinter = None


@unittest.skipIf(tkinter is None, "tkinter is unavailable")
class ThemeToggleTests(unittest.TestCase):
    def setUp(self) -> None:
        from cc_decrypter import gui

        self.gui = gui
        try:
            self.root = tkinter.Tk()
        except tkinter.TclError as exc:  # pragma: no cover - headless machine
            raise unittest.SkipTest(f"no display available: {exc}")
        self.addCleanup(self.root.destroy)
        self.root.geometry("880x760")

        self.saved: list[str] = []
        patcher = patch.object(gui, "save_theme", self.saved.append)
        patcher.start()
        self.addCleanup(patcher.stop)

        with patch.object(gui.DecrypterApp, "start_scan", lambda self: None), \
                patch.object(gui, "load_theme", lambda: "light"):
            self.app = gui.DecrypterApp(self.root)
        self.root.update()

    def _click_toggle(self, x: int) -> None:
        self.app.toggle_canvas.event_generate("<Button-1>", x=x, y=14)
        self.root.update()

    def test_clicking_the_dark_half_switches_to_dark(self) -> None:
        self._click_toggle(self.gui.THEME_TOGGLE_WIDTH - 10)

        self.assertEqual(self.app.theme, "dark")
        self.assertEqual(self.saved, ["dark"])
        self.assertIs(self.app.c, self.gui.DARK)

    def test_clicking_the_light_half_switches_back(self) -> None:
        self._click_toggle(self.gui.THEME_TOGGLE_WIDTH - 10)
        self._click_toggle(10)

        self.assertEqual(self.app.theme, "light")
        self.assertEqual(self.saved, ["dark", "light"])

    def test_clicking_the_active_half_changes_nothing(self) -> None:
        self._click_toggle(10)

        self.assertEqual(self.app.theme, "light")
        self.assertEqual(self.saved, [])

    def test_the_selected_half_is_highlighted(self) -> None:
        canvas = self.app.toggle_canvas
        track, knob = canvas.find_all()[:2]
        half = self.gui.THEME_TOGGLE_WIDTH / 2

        self.assertLess(max(canvas.coords(knob)[0::2]), half + 1)
        self.assertNotEqual(canvas.itemcget(knob, "fill"), canvas.itemcget(track, "fill"))

        self._click_toggle(self.gui.THEME_TOGGLE_WIDTH - 10)

        canvas = self.app.toggle_canvas
        track, knob = canvas.find_all()[:2]
        self.assertGreater(min(canvas.coords(knob)[0::2]), half - 1)
        self.assertNotEqual(canvas.itemcget(knob, "fill"), canvas.itemcget(track, "fill"))

    def test_no_widget_in_the_main_window_changes_the_mouse_cursor(self) -> None:
        # text fields in the other windows keep the platform I-beam; nothing in
        # the main window may swap the pointer for a hand or anything else.
        def walk(widget):
            yield widget
            for child in widget.winfo_children():
                yield from walk(child)

        changed = [
            str(widget) for widget in walk(self.root) if widget.cget("cursor") not in ("", "arrow")
        ]

        self.assertEqual(changed, [])


if __name__ == "__main__":
    unittest.main()
