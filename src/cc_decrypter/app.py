from __future__ import annotations

import platform
import sys
import traceback
from datetime import datetime
from pathlib import Path


LOG_DIR = Path.home() / "Library" / "Logs" / "CC Decrypter"
LOG_PATH = LOG_DIR / "startup.log"
SMOKE_TEST_ARG = "--smoke-test"


def _write_startup_log(message: str) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")
    except OSError:
        pass


def _run_smoke_test() -> None:
    _write_startup_log("running smoke test")

    from tkinter import Tk

    root = Tk()
    root.withdraw()
    root.update_idletasks()
    root.destroy()
    print("CC Decrypter smoke test passed")


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv

    _write_startup_log(
        "starting "
        f"python={sys.version.split()[0]} "
        f"machine={platform.machine()} "
        f"system={platform.platform()}"
    )

    try:
        if SMOKE_TEST_ARG in args:
            _run_smoke_test()
            return

        from cc_decrypter.gui import main as gui_main

        gui_main()
    except Exception:
        _write_startup_log(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
