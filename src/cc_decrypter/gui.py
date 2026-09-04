from __future__ import annotations

import math
import threading
from collections import deque
from pathlib import Path
from tkinter import (
    BOTH,
    BOTTOM,
    END,
    LEFT,
    RIGHT,
    TOP,
    X,
    Button,
    Canvas,
    Entry,
    Frame,
    Label,
    StringVar,
    Tk,
    Toplevel,
    scrolledtext,
)
from tkinter import filedialog, font as tkfont, messagebox

from cc_decrypter.decoder import DecodeError, decode_file
from cc_decrypter.discovery import (
    DraftVideo,
    default_drafts_root,
    find_protected_videos,
    output_path_for,
)
from cc_decrypter.settings import (
    detect_system_theme,
    load_drafts_folder,
    load_theme,
    save_drafts_folder,
    save_theme,
)


LIGHT = {
    "bg": "#ffffff",
    "text": "#14171a",
    "body": "#4b5560",
    "muted": "#8a8f98",
    "faint": "#b9bec7",
    "hairline": "#eceef2",
    "row_line": "#f4f5f7",
    "pill_bg": "#f6f7f9",
    "pill_border": "#e8eaee",
    "check_border": "#cfd4db",
    "check_fill": "#ffffff",
    "accent": "#2f6bff",
    "accent_text": "#2f6bff",
    "accent_active": "#245bd9",
    "disabled_fill": "#e9ecf1",
    "disabled_text": "#9aa0aa",
    "entry_bg": "#ffffff",
}
DARK = {
    "bg": "#1e2025",
    "text": "#e8eaee",
    "body": "#c9cdd4",
    "muted": "#8a8f98",
    "faint": "#6b7280",
    "hairline": "#31343c",
    "row_line": "#2a2d34",
    "pill_bg": "#26282e",
    "pill_border": "#31343c",
    "check_border": "#4a4f59",
    "check_fill": "#26282e",
    "accent": "#3d78ff",
    "accent_text": "#5c93ff",
    "accent_active": "#2f6bff",
    "disabled_fill": "#2a2d33",
    "disabled_text": "#6b7280",
    "entry_bg": "#26282e",
}
GREEN = "#34c759"
AMBER = "#e8a13c"
RED = "#e5484d"

CONTENT_WIDTH = 640
ROW_HEIGHT = 48
VISIBLE_ROWS = 8
LIST_HEIGHT = ROW_HEIGHT * VISIBLE_ROWS


def human_size(size: int) -> str:
    if size >= 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / 1024:.0f} KB"


class DecrypterApp:
    def __init__(self, root: Tk):
        self.root = root
        root.title("CC Decrypter")
        root.geometry("880x760")
        root.minsize(720, 680)

        self.f_title = tkfont.Font(size=-21, weight="bold")
        self.f_sub = tkfont.Font(size=-12)
        self.f_step = tkfont.Font(size=-10, weight="bold")
        self.f_name = tkfont.Font(size=-12)
        self.f_small = tkfont.Font(size=-10)
        self.f_small_bold = tkfont.Font(size=-10, weight="bold")
        self.f_status = tkfont.Font(size=-11)
        self.f_cta = tkfont.Font(size=-13, weight="bold")
        self.f_check = tkfont.Font(size=-9, weight="bold")
        mono_family = "Menlo" if "Menlo" in tkfont.families(root) else "Courier"
        self.f_mono = tkfont.Font(family=mono_family, size=-10)

        self.theme = load_theme() or detect_system_theme()
        self.c = DARK if self.theme == "dark" else LIGHT
        self._status = ("neutral", "Starting…")

        self._results: list[DraftVideo] = []
        self._selected: set[int] = set()
        self._busy = False
        self._log_buffer: deque[str] = deque(maxlen=500)
        self._log_window: Toplevel | None = None
        self._log_text = None
        self._single_window: Toplevel | None = None
        self._single_log = None
        self._single_button: Button | None = None

        self.input_var = StringVar()
        self.output_var = StringVar()
        saved_folder = load_drafts_folder()
        if saved_folder is not None and saved_folder.is_dir():
            self.drafts_path = saved_folder
        else:
            self.drafts_path = default_drafts_root() or (
                Path.home()
                / "Movies"
                / "CapCut"
                / "User Data"
                / "Projects"
                / "com.lveditor.draft"
            )
        self.output_dir = Path.home() / "CC Decrypter Exports"

        self._build_ui()

        if self.drafts_path.is_dir():
            self.start_scan()
        else:
            self._set_status("working", "Drafts folder not found — click the path above to choose it.")

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        if getattr(self, "content", None) is not None:
            self.content.destroy()
        self.root.configure(bg=self.c["bg"])

        content = Frame(self.root, bg=self.c["bg"])
        content.place(relx=0.5, anchor="n", y=0, width=CONTENT_WIDTH, relheight=1.0)
        self.content = content

        footer = Frame(content, bg=self.c["bg"])
        footer.pack(side=BOTTOM, fill=X, pady=(0, 14))
        Frame(content, bg=self.c["hairline"], height=1).pack(side=BOTTOM, fill=X)

        main = Frame(content, bg=self.c["bg"])
        main.pack(side=TOP, fill=BOTH, expand=True)

        intro = Frame(main, bg=self.c["bg"])
        intro.pack(fill=X, pady=(26, 0))
        Label(intro, text="CC Decrypter", font=self.f_title, fg=self.c["text"], bg=self.c["bg"]).pack()
        Label(
            intro,
            text="Videos from your CapCut drafts, decrypted into normal MP4 files.",
            font=self.f_sub,
            fg=self.c["muted"],
            bg=self.c["bg"],
        ).pack(pady=(4, 0))

        Label(
            main,
            text="1 · DRAFTS FOLDER",
            font=self.f_step,
            fg=self.c["muted"],
            bg=self.c["bg"],
            anchor="w",
        ).pack(fill=X, pady=(22, 6))
        self._build_folder_pill(main)

        Label(
            main,
            text="2 · PICK VIDEOS TO DECRYPT",
            font=self.f_step,
            fg=self.c["muted"],
            bg=self.c["bg"],
            anchor="w",
        ).pack(fill=X, pady=(20, 6))

        self.list_canvas = Canvas(
            main,
            width=CONTENT_WIDTH,
            height=LIST_HEIGHT,
            bg=self.c["bg"],
            highlightthickness=1,
            highlightbackground=self.c["hairline"],
            yscrollincrement=20,
        )
        self.list_canvas.pack(fill=X)
        self.list_canvas.bind("<Button-1>", self._on_list_click)
        self.list_canvas.bind("<Double-Button-1>", self._on_list_double_click)
        self.list_canvas.bind("<MouseWheel>", self._on_list_wheel)
        self.list_canvas.bind("<Button-4>", lambda e: self.list_canvas.yview_scroll(-1, "units"))
        self.list_canvas.bind("<Button-5>", lambda e: self.list_canvas.yview_scroll(1, "units"))

        self.counts_label = Label(main, font=self.f_status, fg=self.c["muted"], bg=self.c["bg"])
        self.counts_label.pack(pady=(14, 10))

        self.cta_canvas = Canvas(
            main, width=CONTENT_WIDTH, height=46, bg=self.c["bg"], highlightthickness=0
        )
        self.cta_canvas.pack(fill=X)
        self.cta_canvas.bind("<Button-1>", self._on_cta_click)

        saverow = Frame(main, bg=self.c["bg"])
        saverow.pack(fill=X, pady=(10, 0))
        inner = Frame(saverow, bg=self.c["bg"])
        inner.pack()
        Label(inner, text="Saved to", font=self.f_status, fg=self.c["muted"], bg=self.c["bg"]).pack(side=LEFT)
        self.savelink = Label(
            inner,
            text=f"  {self._display_dir()}  ",
            font=self.f_mono,
            fg=self.c["body"],
            bg=self.c["bg"],
        )
        self.savelink.pack(side=LEFT)
        change = Label(
            inner,
            text="· Change…",
            font=self.f_status,
            fg=self.c["accent_text"],
            bg=self.c["bg"],
            cursor="hand2",
        )
        change.pack(side=LEFT)
        change.bind("<Button-1>", self._on_change_output)
        self.savelink.bind("<Button-1>", self._on_change_output)
        self.savelink.config(cursor="hand2")

        status_row = Frame(footer, bg=self.c["bg"])
        status_row.pack(side=LEFT)
        self.status_dot = Canvas(
            status_row, width=10, height=10, bg=self.c["bg"], highlightthickness=0
        )
        self.status_dot.pack(side=LEFT, padx=(2, 6))
        self._status_dot_id = self.status_dot.create_oval(1, 1, 9, 9, fill=self.c["muted"], outline="")
        self.status_label = Label(
            status_row, text="", font=self.f_status, fg=self.c["muted"], bg=self.c["bg"]
        )
        self.status_label.pack(side=LEFT)

        browse_link = Label(
            footer,
            text="Have a single file? Browse…",
            font=self.f_status,
            fg=self.c["muted"],
            bg=self.c["bg"],
            cursor="hand2",
        )
        browse_link.pack(side=RIGHT)
        browse_link.bind("<Button-1>", lambda e: self.show_single_file())
        log_link = Label(
            footer,
            text="View log  ",
            font=self.f_status,
            fg=self.c["accent_text"],
            bg=self.c["bg"],
            cursor="hand2",
        )
        log_link.pack(side=RIGHT)
        log_link.bind("<Button-1>", lambda e: self.show_log())

        self._draw_folder_pill()
        self._draw_list()
        self._update_counts()
        self._update_cta()
        self._apply_status()
        # built last so it stacks above the packed frames it overlaps
        self._build_theme_toggle(content)

    def _build_theme_toggle(self, parent: Frame) -> None:
        canvas = Canvas(
            parent, width=34, height=34, bg=self.c["bg"], highlightthickness=0
        )
        canvas.place(x=CONTENT_WIDTH - 34, y=14)
        self.toggle_canvas = canvas
        self._draw_theme_icon(canvas)
        canvas.tag_bind("t", "<Button-1>", self._on_toggle_theme)
        canvas.tag_bind("t", "<Enter>", lambda e: canvas.config(cursor="hand2"))
        canvas.tag_bind("t", "<Leave>", lambda e: canvas.config(cursor=""))

    def _draw_theme_icon(self, canvas: Canvas) -> None:
        canvas.delete("all")
        color = self.c["muted"]
        if self.theme == "light":  # show a moon: "switch to dark"
            canvas.create_oval(7, 7, 27, 27, fill=color, outline="", tags=("t",))
            canvas.create_oval(14, 3, 33, 22, fill=self.c["bg"], outline="", tags=("t",))
        else:  # show a sun: "switch to light"
            canvas.create_oval(12, 12, 22, 22, fill=color, outline="", tags=("t",))
            for step in range(8):
                angle = step * math.pi / 4
                dx = math.cos(angle)
                dy = math.sin(angle)
                canvas.create_line(
                    17 + 8 * dx, 17 + 8 * dy, 17 + 11.5 * dx, 17 + 11.5 * dy,
                    fill=color, width=1,
                )

    def _build_folder_pill(self, parent: Frame) -> None:
        self.folder_canvas = Canvas(
            parent, width=CONTENT_WIDTH, height=36, bg=self.c["bg"], highlightthickness=0
        )
        self.folder_canvas.pack(fill=X)
        self.folder_canvas.tag_bind("pick", "<Button-1>", self._on_choose_folder)
        self.folder_canvas.tag_bind("choose", "<Button-1>", self._on_choose_folder)
        self.folder_canvas.tag_bind("rescan", "<Button-1>", lambda e: self.start_scan())
        for tag in ("pick", "choose", "rescan"):
            self.folder_canvas.tag_bind(
                tag, "<Enter>", lambda e: self.folder_canvas.config(cursor="hand2")
            )
            self.folder_canvas.tag_bind(
                tag, "<Leave>", lambda e: self.folder_canvas.config(cursor="")
            )

    def _draw_folder_pill(self) -> None:
        canvas = self.folder_canvas
        canvas.delete("all")
        self._round_rect(
            canvas, 1, 1, CONTENT_WIDTH - 1, 35, 18,
            fill=self.c["pill_bg"], outline=self.c["pill_border"], tags=("pick",),
        )
        canvas.create_text(20, 18, text="📁", font=self.f_small, tags=("pick",))
        self._folder_text_id = canvas.create_text(
            42, 18, anchor="w", text="", font=self.f_mono, fill=self.c["body"], tags=("pick",)
        )
        canvas.create_rectangle(
            CONTENT_WIDTH - 168, 4, CONTENT_WIDTH - 100, 32,
            fill=self.c["pill_bg"], outline="", tags=("choose",),
        )
        canvas.create_text(
            CONTENT_WIDTH - 106, 18, anchor="e", text="Choose…",
            font=self.f_small_bold, fill=self.c["accent_text"], tags=("choose",),
        )
        canvas.create_rectangle(
            CONTENT_WIDTH - 92, 4, CONTENT_WIDTH - 10, 32,
            fill=self.c["pill_bg"], outline="", tags=("rescan",),
        )
        canvas.create_text(
            CONTENT_WIDTH - 14, 18, anchor="e", text="Rescan",
            font=self.f_small_bold, fill=self.c["accent_text"], tags=("rescan",),
        )
        self._update_folder_pill()

    def _round_rect(self, canvas: Canvas, x1, y1, x2, y2, r, **kwargs) -> int:
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def _fit_text(self, text: str, font: tkfont.Font, max_px: int) -> str:
        if font.measure(text) <= max_px:
            return text
        while text and font.measure(text + "…") > max_px:
            text = text[:-1]
        return text + "…"

    def _fit_middle(self, text: str, font: tkfont.Font, max_px: int) -> str:
        if font.measure(text) <= max_px:
            return text
        head, tail = text, ""
        while head and font.measure(head + "…" + tail) > max_px:
            if len(head) > len(tail):
                head = head[:-1]
            else:
                tail = tail[1:]
        return head + "…" + tail

    # --------------------------------------------------------- list drawing

    def _update_folder_pill(self) -> None:
        path_text = str(self.drafts_path)
        self.folder_canvas.itemconfigure(
            self._folder_text_id, text=self._fit_middle(path_text, self.f_mono, 460)
        )

    def _draw_list(self) -> None:
        canvas = self.list_canvas
        canvas.delete("all")
        if not self._results:
            canvas.create_text(
                CONTENT_WIDTH / 2, LIST_HEIGHT / 2 - 10,
                text="No protected videos found.", font=self.f_name, fill=self.c["muted"],
            )
            canvas.create_text(
                CONTENT_WIDTH / 2, LIST_HEIGHT / 2 + 14,
                text="Pick your CapCut drafts folder above, then click Rescan.",
                font=self.f_small, fill=self.c["faint"],
            )
            canvas.configure(scrollregion=(0, 0, CONTENT_WIDTH, LIST_HEIGHT))
            return

        for index, video in enumerate(self._results):
            top = index * ROW_HEIGHT
            middle = top + ROW_HEIGHT / 2
            selected = index in self._selected
            canvas.create_oval(
                14, middle - 9, 32, middle + 9,
                outline=self.c["accent"] if selected else self.c["check_border"],
                fill=self.c["accent"] if selected else self.c["check_fill"],
                width=1,
            )
            if selected:
                canvas.create_text(
                    23, middle - 1, text="✓", fill="white", font=self.f_check
                )
            canvas.create_text(
                46, middle - 11, anchor="w",
                text=self._fit_text(video.path.name, self.f_name, 450),
                font=self.f_name, fill=self.c["text"],
            )
            canvas.create_text(
                46, middle + 9, anchor="w",
                text=self._fit_text(self._row_sublabel(video), self.f_small, 460),
                font=self.f_small, fill=self.c["muted"],
            )
            canvas.create_text(
                CONTENT_WIDTH - 14, middle, anchor="e",
                text=human_size(video.size), font=self.f_small, fill=self.c["muted"],
            )
            if index < len(self._results) - 1:
                canvas.create_line(
                    1, top + ROW_HEIGHT, CONTENT_WIDTH - 1, top + ROW_HEIGHT,
                    fill=self.c["row_line"],
                )

        total_height = len(self._results) * ROW_HEIGHT
        canvas.configure(scrollregion=(0, 0, CONTENT_WIDTH, total_height))

    def _row_sublabel(self, video: DraftVideo) -> str:
        parts = []
        if video.project_name:
            parts.append(video.project_name)
        if video.created_label:
            parts.append(f"Created {video.created_label}")
        return " · ".join(parts) if parts else "—"

    def _row_at(self, y_canvas: float) -> int | None:
        index = int(y_canvas // ROW_HEIGHT)
        if 0 <= index < len(self._results):
            return index
        return None

    def _on_list_click(self, event) -> None:
        if self._busy:
            return
        index = self._row_at(self.list_canvas.canvasy(event.y))
        if index is None:
            return
        if index in self._selected:
            self._selected.discard(index)
        else:
            self._selected.add(index)
        self._draw_list()
        self._update_counts()
        self._update_cta()

    def _on_list_double_click(self, event) -> None:
        index = self._row_at(self.list_canvas.canvasy(event.y))
        if index is None or not self._results[index].decryptable:
            return
        self.show_single_file(preset=str(self._results[index].path))

    def _on_list_wheel(self, event) -> None:
        delta = event.delta
        if not delta:
            return
        if abs(delta) >= 120:
            steps = -int(delta / 120)
        else:
            steps = -1 if delta > 0 else 1
        self.list_canvas.yview_scroll(steps, "units")

    def _update_counts(self) -> None:
        if not self._results:
            self.counts_label.config(text="Nothing to decrypt yet.")
            return
        count = len(self._selected)
        total = sum(self._results[i].size for i in self._selected)
        self.counts_label.config(
            text=f"{count} of {len(self._results)} videos selected · {human_size(total)}"
        )

    # ------------------------------------------------------------------ CTA

    def _update_cta(self) -> None:
        canvas = self.cta_canvas
        canvas.delete("all")
        count = len(self._selected)

        if self._busy:
            fill = self.c["disabled_fill"]
            text_color = self.c["disabled_text"]
            label = "Working…"
        elif count == 0:
            fill = self.c["disabled_fill"]
            text_color = self.c["disabled_text"]
            label = "Select videos to decrypt"
        else:
            fill = self.c["accent"]
            text_color = "white"
            label = f"Decrypt {count} video{'s' if count != 1 else ''}"

        self._round_rect(canvas, 1, 1, CONTENT_WIDTH - 1, 45, 23, fill=fill, outline="", tags=("cta",))
        self._cta_text_id = canvas.create_text(
            CONTENT_WIDTH / 2, 23, text=label, font=self.f_cta, fill=text_color, tags=("cta",)
        )
        canvas.config(cursor="hand2" if count and not self._busy else "")

    def _on_cta_click(self, _event) -> None:
        if self._busy or not self._selected:
            return
        self.start_batch()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._update_cta()

    # -------------------------------------------------------------- status

    def _set_status(self, kind: str, message: str) -> None:
        self._status = (kind, message)
        self._apply_status()

    def _apply_status(self) -> None:
        kind, message = self._status
        color = {"ok": GREEN, "working": AMBER, "error": RED}.get(kind, self.c["muted"])
        self.status_dot.itemconfigure(self._status_dot_id, fill=color)
        self.status_label.config(text=message)

    # ---------------------------------------------------------------- theme

    def _on_toggle_theme(self, _event) -> None:
        self.theme = "dark" if self.theme == "light" else "light"
        save_theme(self.theme)
        self._apply_theme()

    def _apply_theme(self) -> None:
        self.c = DARK if self.theme == "dark" else LIGHT
        windows = []
        if self._log_window is not None and self._log_window.winfo_exists():
            windows.append(self.show_log)
            self._close_log()
        if self._single_window is not None and self._single_window.winfo_exists():
            windows.append(self.show_single_file)
            self._close_single()

        self._build_ui()

        for reopen in windows:
            reopen()

    # ------------------------------------------------------------- actions

    def _on_choose_folder(self, _event) -> None:
        path = filedialog.askdirectory(title="Choose your CapCut drafts folder")
        if not path:
            return
        self.drafts_path = Path(path)
        save_drafts_folder(self.drafts_path)
        self._update_folder_pill()
        self.start_scan()

    def _on_change_output(self, _event) -> None:
        path = filedialog.askdirectory(title="Choose where decrypted copies are saved")
        if not path:
            return
        self.output_dir = Path(path)
        self.savelink.config(text=f"  {self._display_dir()}  ")

    def _display_dir(self) -> str:
        home = Path.home()
        try:
            return "~/" + str(self.output_dir.relative_to(home))
        except ValueError:
            return str(self.output_dir)

    def start_scan(self) -> None:
        if self._busy:
            return
        if not self.drafts_path.is_dir():
            messagebox.showerror(
                "Draft folder not found", f"Could not find the folder:\n{self.drafts_path}"
            )
            return
        self._set_busy(True)
        self._results = []
        self._selected.clear()
        self._draw_list()
        self._update_counts()
        self.list_canvas.yview_moveto(0)
        self._set_status("working", "Searching your CapCut drafts folder…")
        self.write_log(f"Searching {self.drafts_path} …")
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self) -> None:
        try:
            results = find_protected_videos(self.drafts_path)
            error = None
        except Exception as exc:  # keep the UI usable no matter what
            results = None
            error = exc
        self.root.after(0, self._scan_finished, results, error)

    def _scan_finished(self, results: list[DraftVideo] | None, error: Exception | None) -> None:
        self._set_busy(False)
        if error is not None or results is None:
            self._set_status("error", "Something went wrong while searching — see the log.")
            self.write_log(f"ERROR while searching: {error}")
            return

        self._results = [video for video in results if video.decryptable]
        unsupported = len(results) - len(self._results)
        self._selected.clear()
        self.list_canvas.yview_moveto(0)
        self._draw_list()
        self._update_counts()
        self._update_cta()

        if self._results:
            self._set_status(
                "ok", f"Found {len(self._results)} videos — click the ones to decrypt."
            )
            self.write_log(f"Found {len(self._results)} video(s) you can decrypt.")
        else:
            self._set_status("neutral", "No protected videos were found in this folder.")
            self.write_log("No protected videos were found in this folder.")
        if unsupported:
            self.write_log(
                f"{unsupported} protected file(s) use an unsupported format and are not shown."
            )

    def start_batch(self) -> None:
        if self._busy or not self._selected:
            return
        videos = [self._results[i] for i in sorted(self._selected)]
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Could not create output folder", str(exc), parent=self.root)
            return

        self._set_busy(True)
        self._set_status("working", f"Decrypting {len(videos)} video(s)…")
        self.write_log(f"Decrypting {len(videos)} video(s) to {self.output_dir} …")
        threading.Thread(
            target=self._batch_worker, args=(videos, self.output_dir), daemon=True
        ).start()

    def _batch_worker(self, videos: list[DraftVideo], output_dir: Path) -> None:
        taken: set[str] = set()
        done = 0
        failed = 0
        for video in videos:
            self.write_log(f"Decrypting: {video.path.name}")
            try:
                target = output_path_for(video, output_dir, taken)
                decode_file(video.path, target, self.write_log)
                done += 1
                self.write_log(f"Saved: {target}")
            except (DecodeError, OSError, ValueError) as exc:
                failed += 1
                self.write_log(f"ERROR: {video.path.name}: {exc}")

        self.root.after(0, self._batch_finished, done, failed, len(videos))

    def _batch_finished(self, done: int, failed: int, total: int) -> None:
        self._set_busy(False)
        if failed:
            self._set_status("error", f"Last run: {done} decrypted · {failed} failed.")
            messagebox.showerror(
                "Some videos failed",
                f"Finished: {done} of {total} video(s) decrypted, {failed} failed.\n"
                "See View log for details.",
                parent=self.root,
            )
        else:
            self._set_status("ok", f"Last run: {done} decrypted · 0 failed.")
            if done:
                messagebox.showinfo(
                    "Done",
                    f"Decrypted {done} video(s).\nSaved to: {self._display_dir()}",
                    parent=self.root,
                )

    # ------------------------------------------------------------ logging

    def write_log(self, message: str) -> None:
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, self.write_log, message)
            return

        self._log_buffer.append(message)
        if self._log_text is not None:
            try:
                self._log_text.insert(END, message + ("\n" if not message.endswith("\n") else ""))
                self._log_text.see(END)
            except Exception:
                pass

    def show_log(self) -> None:
        if self._log_window is not None and self._log_window.winfo_exists():
            self._log_window.lift()
            self._log_window.focus()
            return

        window = Toplevel(self.root)
        window.title("CC Decrypter — Log")
        window.geometry("640x440")
        window.configure(bg=self.c["bg"])
        text = scrolledtext.ScrolledText(
            window, font=self.f_mono, bg=self.c["entry_bg"], fg=self.c["body"],
            insertbackground=self.c["text"],
        )
        text.pack(fill=BOTH, expand=True, padx=10, pady=10)
        for line in self._log_buffer:
            text.insert(END, line + "\n")
        text.see(END)

        self._log_window = window
        self._log_text = text
        window.protocol("WM_DELETE_WINDOW", self._close_log)

    def _close_log(self) -> None:
        if self._log_window is not None:
            self._log_window.destroy()
        self._log_window = None
        self._log_text = None

    # -------------------------------------------------------- single file

    def set_single_input(self, path: str) -> None:
        self.input_var.set(path)
        if not self.output_var.get().strip():
            input_path = Path(path)
            self.output_var.set(str(input_path.with_name(input_path.stem + "_decoded.mp4")))

    def show_single_file(self, preset: str | None = None) -> None:
        if self._single_window is not None and self._single_window.winfo_exists():
            if preset:
                self.set_single_input(preset)
            self._single_window.lift()
            self._single_window.focus()
            return

        window = Toplevel(self.root)
        window.title("Single file — CC Decrypter")
        window.configure(bg=self.c["bg"])
        window.resizable(False, False)
        outer = Frame(window, bg=self.c["bg"], padx=16, pady=14)
        outer.pack(fill=BOTH, expand=True)

        for label_text, variable, command in (
            ("Input file", self.input_var, lambda: self._pick_single_file()),
            ("Output file", self.output_var, lambda: self._pick_single_output()),
        ):
            row = Frame(outer, bg=self.c["bg"])
            row.pack(fill=X, pady=4)
            Label(
                row, text=label_text, width=11, anchor="w",
                bg=self.c["bg"], fg=self.c["body"],
            ).pack(side=LEFT)
            Entry(
                row, textvariable=variable, width=58, relief="flat",
                highlightthickness=1, highlightbackground=self.c["hairline"],
                highlightcolor=self.c["accent"], bg=self.c["entry_bg"],
                fg=self.c["text"], insertbackground=self.c["text"],
            ).pack(side=LEFT, padx=(0, 8))
            Button(
                row, text="Browse", command=command, relief="flat",
                bg=self.c["pill_bg"], fg=self.c["body"],
                activebackground=self.c["pill_border"], activeforeground=self.c["text"],
                padx=10,
            ).pack(side=RIGHT)

        actions = Frame(outer, bg=self.c["bg"])
        actions.pack(fill=X, pady=(10, 8))
        decode_button = Button(
            actions, text="Decode", command=self._start_single_decode, relief="flat",
            bg=self.c["accent"], fg="white",
            activebackground=self.c["accent_active"], activeforeground="white",
            font=self.f_small_bold, padx=18, pady=5,
        )
        decode_button.pack(side=RIGHT)

        log_text = scrolledtext.ScrolledText(
            outer, height=12, width=74, font=self.f_mono,
            bg=self.c["entry_bg"], fg=self.c["body"], insertbackground=self.c["text"],
        )
        log_text.pack(fill=BOTH, expand=True)

        self._single_window = window
        self._single_log = log_text
        self._single_button = decode_button
        window.protocol("WM_DELETE_WINDOW", self._close_single)
        if preset:
            self.set_single_input(preset)

    def _close_single(self) -> None:
        if self._single_window is not None:
            self._single_window.destroy()
        self._single_window = None
        self._single_log = None
        self._single_button = None

    def _pick_single_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose protected video resource",
            filetypes=(("MP4 files", "*.mp4"), ("All files", "*.*")),
        )
        if path:
            self.set_single_input(path)

    def _pick_single_output(self) -> None:
        initial = self.output_var.get().strip()
        path = filedialog.asksaveasfilename(
            title="Save decoded MP4 as",
            initialfile=Path(initial).name if initial else "decoded.mp4",
            defaultextension=".mp4",
            filetypes=(("MP4 files", "*.mp4"), ("All files", "*.*")),
        )
        if path:
            self.output_var.set(path)

    def _single_log_write(self, message: str) -> None:
        if self._single_log is None:
            return
        try:
            if not self._single_log.winfo_exists():
                return
            self._single_log.insert(END, message + ("\n" if not message.endswith("\n") else ""))
            self._single_log.see(END)
        except Exception:
            pass

    def _start_single_decode(self) -> None:
        input_path = Path(self.input_var.get().strip())
        output_path = Path(self.output_var.get().strip())
        button = self._single_button
        if button is not None:
            button.config(state="disabled")

        def logger(message: str) -> None:
            self.write_log(message)
            self._single_log_write(message)

        def worker() -> None:
            try:
                decode_file(input_path, output_path, logger)
                logger("Done.")
            except (DecodeError, OSError, ValueError) as exc:
                logger(f"ERROR: {exc}")
                self.root.after(
                    0, lambda: messagebox.showerror("Decode failed", str(exc), parent=self.root)
                )
            finally:
                def reenable() -> None:
                    if button is not None and button.winfo_exists():
                        button.config(state="normal")

                self.root.after(0, reenable)

        threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    root = Tk()
    DecrypterApp(root)
    root.mainloop()
