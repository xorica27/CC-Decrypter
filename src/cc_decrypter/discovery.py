from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from cc_decrypter.decoder import parse_bdve_footer


VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v"}
PROBE_TAIL_BYTES = 1024 * 1024
MIN_BDVE_FILE_SIZE = 68
UNSAFE_NAME_CHARS = re.compile(r'[\\/:*?"<>|]')
DRAFT_SUBPATH = Path("User Data") / "Projects" / "com.lveditor.draft"
# CapCut international first, then the Chinese JianyingPro build
EDITOR_FOLDERS = ("CapCut", "JianyingPro")
# the Mac App Store build is sandboxed, so its drafts live under its container
MACOS_SANDBOX_CONTAINERS = ("com.lemon.lvoverseas",)
OUTPUT_FOLDER_NAME = "CC Decrypter Exports"


@dataclass(frozen=True)
class DraftVideo:
    path: Path
    relative: Path
    size: int
    cryptor_type: int
    created: float = 0.0

    @property
    def decryptable(self) -> bool:
        return self.cryptor_type == 1

    @property
    def project_name(self) -> str:
        parts = self.relative.parts
        return parts[0] if len(parts) > 1 else ""

    @property
    def created_label(self) -> str:
        if self.created <= 0:
            return ""
        moment = datetime.fromtimestamp(self.created)
        return f"{moment.strftime('%b')} {moment.day}, {moment.year}"


def candidate_drafts_roots() -> list[Path]:
    """Every place this platform is known to keep CapCut drafts, best first."""
    home = Path.home()
    roots = []
    if sys.platform == "win32":
        local = Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
        for editor in EDITOR_FOLDERS:
            roots.append(local / editor / DRAFT_SUBPATH)
    else:
        for editor in EDITOR_FOLDERS:
            roots.append(home / "Movies" / editor / DRAFT_SUBPATH)
        for container in MACOS_SANDBOX_CONTAINERS:
            for editor in EDITOR_FOLDERS:
                roots.append(
                    home / "Library" / "Containers" / container / "Data" / "Movies"
                    / editor / DRAFT_SUBPATH
                )
    return roots


def default_drafts_path() -> Path:
    """Where drafts normally live on this platform, whether or not it exists."""
    return candidate_drafts_roots()[0]


def default_drafts_root() -> Path | None:
    """The first candidate that is actually there, or None."""
    for root in candidate_drafts_roots():
        if root.is_dir():
            return root
    return None


def resolve_drafts_folder(saved: Path | None) -> tuple[Path, Path | None]:
    """Pick the folder to open with.

    Returns the folder to use plus the saved folder when it has gone missing,
    so the caller can say so instead of quietly scanning somewhere else.
    """
    if saved is not None and saved.is_dir():
        return saved, None
    return default_drafts_root() or default_drafts_path(), saved


def default_output_dir() -> Path:
    return Path.home() / OUTPUT_FOLDER_NAME


def resolve_output_folder(saved: Path | None) -> Path:
    """Use the saved output folder while it is still somewhere we could write.

    The folder itself is only created at decrypt time, so a saved path that
    does not exist yet is fine as long as its parent is there.
    """
    if saved is not None and (saved.is_dir() or saved.parent.is_dir()):
        return saved
    return default_output_dir()


def probe_cryptor_type(path: Path) -> int | None:
    """Return the cryptor type from the file's trailing BDVE footer, or None.

    Only the tail of the file is read so scanning stays fast; footers larger
    than PROBE_TAIL_BYTES are not detected.
    """
    try:
        size = path.stat().st_size
        if size < MIN_BDVE_FILE_SIZE:
            return None
        with path.open("rb") as handle:
            head = handle.read(8)
            if head[4:8] == b"ftyp":
                # Content already starts with a plain ftyp box, so the engine
                # cannot decrypt it even when a footer is still attached.
                return None
            handle.seek(-min(size, PROBE_TAIL_BYTES), os.SEEK_END)
            tail = handle.read()
    except OSError:
        return None

    footer = parse_bdve_footer(tail)
    return None if footer is None else footer.cryptor_type


def find_protected_videos(root: Path) -> list[DraftVideo]:
    if not root.is_dir():
        return []

    found: list[DraftVideo] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix.lower() not in VIDEO_SUFFIXES:
                continue
            cryptor_type = probe_cryptor_type(path)
            if cryptor_type is None:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            birth = getattr(stat, "st_birthtime", None)
            found.append(
                DraftVideo(
                    path=path,
                    relative=path.relative_to(root),
                    size=stat.st_size,
                    cryptor_type=cryptor_type,
                    created=birth if birth is not None else stat.st_ctime,
                )
            )

    found.sort(key=lambda video: str(video.relative).lower())
    return found


def export_base_name(video: DraftVideo) -> str:
    """The name a decrypted copy gets, before any (2) suffix."""
    project = UNSAFE_NAME_CHARS.sub("_", video.project_name)
    stem = UNSAFE_NAME_CHARS.sub("_", video.path.stem)
    return f"{project}_{stem}_decoded" if project else f"{stem}_decoded"


def existing_export(video: DraftVideo, output_dir: Path) -> Path | None:
    """The decrypted copy already sitting in the output folder, if there is one."""
    candidate = output_dir / f"{export_base_name(video)}.mp4"
    return candidate if candidate.exists() else None


def output_path_for(video: DraftVideo, output_dir: Path, taken: set[str] | None = None) -> Path:
    """Pick a non-clobbering output path like <project>_<stem>_decoded.mp4."""
    taken = taken if taken is not None else set()

    base = export_base_name(video)

    candidate = output_dir / f"{base}.mp4"
    counter = 2
    while str(candidate) in taken or candidate.exists():
        candidate = output_dir / f"{base} ({counter}).mp4"
        counter += 1

    taken.add(str(candidate))
    return candidate
