from __future__ import annotations

import threading
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Button, Entry, Frame, Label, StringVar, Tk
from tkinter import filedialog, messagebox, scrolledtext

from cc_decrypter.decoder import DecodeError, decode_file


class DecrypterApp:
    def __init__(self, root: Tk):
        self.root = root
        root.title("CC Decrypter")
        root.geometry("820x540")

        self.input_var = StringVar()
        self.output_var = StringVar()
        self._build_ui()

    def _build_ui(self) -> None:
        outer = Frame(self.root, padx=12, pady=12)
        outer.pack(fill=BOTH, expand=True)

        self._path_row(outer, "Input file", self.input_var, self.pick_input)
        self._path_row(outer, "Output file", self.output_var, self.pick_output)

        actions = Frame(outer)
        actions.pack(fill=X, pady=(8, 10))
        Button(actions, text="Decode", command=self.start_decode).pack(side=RIGHT)

        self.log = scrolledtext.ScrolledText(outer, height=24)
        self.log.pack(fill=BOTH, expand=True)
        self.write_log("Choose a protected draft video resource, then Decode.\n")

    def _path_row(self, parent: Frame, label: str, variable: StringVar, command) -> None:
        row = Frame(parent)
        row.pack(fill=X, pady=4)
        Label(row, text=label, width=11, anchor="w").pack(side=LEFT)
        Entry(row, textvariable=variable).pack(side=LEFT, fill=X, expand=True, padx=(0, 8))
        Button(row, text="Browse", command=command).pack(side=RIGHT)

    def write_log(self, message: str) -> None:
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, self.write_log, message)
            return

        self.log.insert(END, message + ("\n" if not message.endswith("\n") else ""))
        self.log.see(END)
        self.root.update_idletasks()

    def pick_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose protected video resource",
            filetypes=(("MP4 files", "*.mp4"), ("All files", "*.*")),
        )
        if not path:
            return

        self.input_var.set(path)
        if not self.output_var.get().strip():
            input_path = Path(path)
            self.output_var.set(str(input_path.with_name(input_path.stem + "_decoded.mp4")))

    def pick_output(self) -> None:
        initial = self.output_var.get().strip()
        path = filedialog.asksaveasfilename(
            title="Save decoded MP4 as",
            initialfile=Path(initial).name if initial else "decoded.mp4",
            defaultextension=".mp4",
            filetypes=(("MP4 files", "*.mp4"), ("All files", "*.*")),
        )
        if path:
            self.output_var.set(path)

    def start_decode(self) -> None:
        input_path = Path(self.input_var.get().strip())
        output_path = Path(self.output_var.get().strip())
        self.log.delete("1.0", END)

        thread = threading.Thread(
            target=self._decode_worker,
            args=(input_path, output_path),
            daemon=True,
        )
        thread.start()

    def _decode_worker(self, input_path: Path, output_path: Path) -> None:
        try:
            decode_file(input_path, output_path, self.write_log)
            self.write_log("Done.")
        except (DecodeError, OSError, ValueError) as exc:
            self.write_log(f"ERROR: {exc}")
            self.root.after(0, lambda: messagebox.showerror("Decode failed", str(exc)))


def main() -> None:
    root = Tk()
    DecrypterApp(root)
    root.mainloop()
