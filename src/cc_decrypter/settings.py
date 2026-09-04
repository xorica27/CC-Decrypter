"""Persisted user settings for CC Decrypter."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

THEMES = ("light", "dark")


def settings_path() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "CC Decrypter" / "settings.json"


def load_settings() -> dict:
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load_theme() -> str | None:
    theme = load_settings().get("theme")
    return theme if theme in THEMES else None


def save_theme(theme: str) -> None:
    if theme not in THEMES:
        raise ValueError(f"unknown theme: {theme}")
    _update_settings({"theme": theme})


def load_drafts_folder() -> Path | None:
    value = load_settings().get("drafts_folder")
    if isinstance(value, str) and value:
        return Path(value)
    return None


def save_drafts_folder(folder: Path | str) -> None:
    _update_settings({"drafts_folder": str(folder)})


def detect_system_theme() -> str:
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0 and "dark" in result.stdout.lower():
                return "dark"
        except (OSError, subprocess.SubprocessError):
            pass
    return "light"


def _update_settings(updates: dict) -> None:
    path = settings_path()
    try:
        data = load_settings()
        data.update(updates)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass
