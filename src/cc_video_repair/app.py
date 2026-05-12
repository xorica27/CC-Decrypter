from __future__ import annotations

import platform
import sys
import traceback
from datetime import datetime
from pathlib import Path


LOG_DIR = Path.home() / "Library" / "Logs" / "CC Video Repair"
LOG_PATH = LOG_DIR / "startup.log"


def _write_startup_log(message: str) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")
    except OSError:
        pass


def main() -> None:
    _write_startup_log(
        "starting "
        f"python={sys.version.split()[0]} "
        f"machine={platform.machine()} "
        f"system={platform.platform()}"
    )

    try:
        from cc_video_repair.gui import main as gui_main

        gui_main()
    except Exception:
        _write_startup_log(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
