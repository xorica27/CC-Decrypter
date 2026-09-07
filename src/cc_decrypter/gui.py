"""The CC Decrypter window, built on Qt.

The list, its scrolling, hit testing, hover and keyboard handling all belong to
Qt here. This module only says what a row looks like and what a click means.
"""

from __future__ import annotations

import sys
import threading
from collections import deque
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QDesktopServices,
    QKeySequence,
    QColor,
    QFont,
    QGuiApplication,
    QPainter,
    QPalette,
    QPen,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenuBar,
    QMessageBox,
    QProgressBar,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from cc_decrypter import __version__
from cc_decrypter.decoder import DecodeError, decode_file
from cc_decrypter.discovery import (
    DraftVideo,
    existing_export,
    find_protected_videos,
    output_path_for,
    resolve_drafts_folder,
    resolve_output_folder,
)
from cc_decrypter.settings import (
    load_drafts_folder,
    load_output_folder,
    load_sort,
    load_theme,
    load_window_geometry,
    save_drafts_folder,
    save_output_folder,
    save_sort,
    save_theme,
    save_window_geometry,
)

RELEASES_URL = "https://github.com/xorica27/CC-Decrypter/releases"
LATEST_RELEASE_API = "https://api.github.com/repos/xorica27/CC-Decrypter/releases/latest"

ACCENT = "#2f6bff"
GREEN = "#34c759"
AMBER = "#e8a13c"
RED = "#e5484d"
GREY = "#8a8f98"

LIGHT_TOKENS = {
    "accent": ACCENT,
    "accent_hover": "#245bd9",
    "surface": "#f5f6f8",
    "surface_hover": "#e9ebef",
    "border": "#e4e7ec",
    "list_bg": "#ffffff",
    "disabled_bg": "#edeff3",
    "disabled_fg": "#a2a8b2",
    "window": "#f2f3f5",
    "text": "#14171a",
}
DARK_TOKENS = {
    "accent": ACCENT,
    "accent_hover": "#5285ff",
    "surface": "#26282e",
    "surface_hover": "#31343c",
    "border": "#33363e",
    "list_bg": "#1b1d21",
    "disabled_bg": "#2a2d33",
    "disabled_fg": "#6b7280",
    "window": "#1e2025",
    "text": "#e8eaee",
}

EXPORTED_ROLE = Qt.ItemDataRole.UserRole + 1
ROW_HEIGHT = 60
CONTENT_WIDTH = 660
# label, sort key, and whether that column starts on its largest/newest value
SORT_OPTIONS = (
    ("Date", "date", True),
    ("Name", "name", False),
    ("Size", "size", True),
)
SORT_KEYS = {
    "date": lambda video: video.created,
    "name": lambda video: video.path.name.lower(),
    "size": lambda video: video.size,
}

def tokens(theme: str | None = None) -> dict[str, str]:
    """Colours for an explicit choice, or for whatever the system is showing."""
    scheme = theme or current_color_scheme()
    return DARK_TOKENS if scheme == "dark" else LIGHT_TOKENS


def stylesheet(theme: str | None = None) -> str:
    t = tokens(theme)
    return f"""
QLabel#step {{ color: {GREY}; font-size: 11px; font-weight: 700; }}
QLabel#subtitle, QLabel#counts {{ color: {GREY}; }}

QFrame#pill {{
    background: {t["surface"]};
    border: 1px solid {t["border"]};
    border-radius: 11px;
}}
QLabel#path {{ color: palette(text); }}

QToolButton#link {{
    color: {t["accent"]};
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 5px 9px;
    font-weight: 600;
}}
QToolButton#link:hover {{ background: {t["surface_hover"]}; }}
QToolButton#link:pressed {{ background: {t["border"]}; }}

QToolButton#sort {{
    color: {GREY};
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px 9px;
    font-weight: 600;
}}
QToolButton#sort:hover {{ background: {t["surface_hover"]}; }}
QToolButton#sort[active="true"] {{ color: {t["accent"]}; }}

QToolButton#segment {{
    background: {t["surface"]};
    border: 1px solid {t["border"]};
    color: {GREY};
    font-size: 14px;
    padding: 0;
}}
QToolButton#segment[side="light"] {{
    border-top-left-radius: 9px; border-bottom-left-radius: 9px; border-right: none;
}}
QToolButton#segment[side="dark"] {{
    border-top-right-radius: 9px; border-bottom-right-radius: 9px;
}}
QToolButton#segment:hover {{ background: {t["surface_hover"]}; }}
QToolButton#segment:checked {{ background: {t["list_bg"]}; color: palette(text); }}

QListWidget {{
    background: {t["list_bg"]};
    border: 1px solid {t["border"]};
    border-radius: 11px;
    padding: 4px 0px;
    outline: none;
}}

QPushButton#cta {{
    background: {t["accent"]};
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 15px;
    font-weight: 600;
}}
QPushButton#cta:hover:enabled {{ background: {t["accent_hover"]}; }}
QPushButton#cta:disabled {{ background: {t["disabled_bg"]}; color: {t["disabled_fg"]}; }}
"""


def human_size(size: int) -> str:
    if size >= 1024 ** 3:
        return f"{size / 1024 ** 3:.1f} GB"
    if size >= 1024 ** 2:
        return f"{size / 1024 ** 2:.1f} MB"
    return f"{size / 1024:.0f} KB"


class ElidingPathLabel(QLabel):
    """Shows a path, shortened in the middle to whatever width it is given."""

    clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._full = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def setFullText(self, text: str) -> None:  # noqa: N802 - matches Qt naming
        self._full = text
        self.setToolTip(text)
        self._elide()

    def _elide(self) -> None:
        available = max(40, self.contentsRect().width())
        self.setText(self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideMiddle, available))

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        self._elide()

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self.clicked.emit()
        super().mousePressEvent(event)


class VideoRow(QStyledItemDelegate):
    """Draws one video. Qt decides which row this is and what state it is in."""

    def sizeHint(self, option, index) -> QSize:  # noqa: N802 - Qt naming
        return QSize(0, ROW_HEIGHT)

    def paint(self, painter: QPainter, option, index) -> None:
        video: DraftVideo = index.data(Qt.ItemDataRole.UserRole)
        if video is None:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        palette = option.palette
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        accent = QColor(ACCENT)
        text_color = palette.text().color()
        muted = QColor(text_color)
        muted.setAlpha(140)

        rect = option.rect
        body = rect.adjusted(8, 2, -8, -2)
        if selected or hovered:
            tint = QColor(accent if selected else text_color)
            tint.setAlpha(34 if selected else 14)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(tint)
            painter.drawRoundedRect(body, 9, 9)

        circle = rect.adjusted(22, (ROW_HEIGHT - 20) // 2, 0, 0)
        circle.setSize(QSize(20, 20))
        if selected:
            painter.setBrush(accent)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(circle)
            pen = QPen(QColor("white"), 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(circle.left() + 5, circle.center().y() + 1,
                             circle.center().x() - 1, circle.bottom() - 5)
            painter.drawLine(circle.center().x() - 1, circle.bottom() - 5,
                             circle.right() - 4, circle.top() + 6)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(muted, 1))
            painter.drawEllipse(circle)

        size_font = QFont(option.font)
        size_font.setPointSizeF(option.font.pointSizeF() - 1)
        painter.setFont(size_font)
        size_text = human_size(video.size)
        if index.data(EXPORTED_ROLE):
            size_text = f"exported · {size_text}"
        size_width = painter.fontMetrics().horizontalAdvance(size_text) + 12
        painter.setPen(muted)
        painter.drawText(
            rect.adjusted(0, 0, -24, 0),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            size_text,
        )

        text_left = rect.left() + 58
        text_width = max(40, rect.width() - 58 - 24 - size_width)

        name_font = QFont(option.font)
        name_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(name_font)
        painter.setPen(text_color)
        name_rect = rect.adjusted(0, 11, 0, 0)
        name_rect.setLeft(text_left)
        name_rect.setWidth(text_width)
        name_rect.setHeight(18)
        painter.drawText(
            name_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            painter.fontMetrics().elidedText(
                video.path.name, Qt.TextElideMode.ElideMiddle, text_width
            ),
        )

        sub_font = QFont(option.font)
        sub_font.setPointSizeF(option.font.pointSizeF() - 1.5)
        painter.setFont(sub_font)
        painter.setPen(muted)
        parts = [part for part in (video.project_name, _created_label(video)) if part]
        sub_rect = name_rect.translated(0, 19)
        painter.drawText(
            sub_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            painter.fontMetrics().elidedText(
                " · ".join(parts) or "—", Qt.TextElideMode.ElideMiddle, text_width
            ),
        )

        if not (selected or hovered):
            line = QColor(text_color)
            line.setAlpha(20)
            painter.setPen(QPen(line, 1))
            painter.drawLine(rect.left() + 22, rect.bottom(), rect.right() - 22, rect.bottom())
        painter.restore()


def version_tuple(version: str) -> tuple[int, ...]:
    """0.3.1 -> (0, 3, 1); anything unparsable sorts lowest."""
    numbers = []
    for part in version.strip().lstrip("vV").split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        if not digits:
            break
        numbers.append(int(digits))
    return tuple(numbers)


def latest_release() -> str:
    """Ask GitHub for the newest published version. Network call; raises on failure."""
    import json
    import urllib.request

    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": f"CC-Decrypter/{__version__}"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.load(response)
    tag = payload.get("tag_name") or ""
    return str(tag).lstrip("vV")


def reveal(path: Path) -> None:
    """Show a folder in Finder or Explorer."""
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def _created_label(video: DraftVideo) -> str:
    return f"Created {video.created_label}" if video.created_label else ""


def support_details() -> str:
    """The facts worth pasting into a bug report."""
    import platform
    import sys

    from PySide6 import __version__ as pyside_version
    from PySide6.QtCore import qVersion

    from cc_decrypter.app import LOG_PATH
    from cc_decrypter.settings import settings_path

    if sys.platform == "darwin":
        os_name = f"macOS {platform.mac_ver()[0]}"
    elif sys.platform == "win32":
        os_name = f"Windows {platform.release()}"
    else:
        os_name = platform.platform()

    return "\n".join(
        [
            f"CC Decrypter {__version__}",
            f"{os_name} ({platform.machine()})",
            f"Qt {qVersion()} · PySide6 {pyside_version} · Python {sys.version.split()[0]}",
            f"Settings: {settings_path()}",
            f"Startup log: {LOG_PATH}",
        ]
    )


class AboutDialog(QDialog):
    update_checked = Signal(str, str)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.update_checked.connect(self._show_update)
        self.setWindowTitle("About CC Decrypter")
        self.setMinimumWidth(470)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(8)

        name = QLabel("CC Decrypter")
        name_font = name.font()
        name_font.setPointSize(name_font.pointSize() + 6)
        name_font.setBold(True)
        name.setFont(name_font)
        layout.addWidget(name)

        version = QLabel(f"Version {__version__}")
        version.setObjectName("subtitle")
        layout.addWidget(version)

        summary = QLabel(
            "Turns supported CC video files from your CapCut drafts folder into "
            "normal MP4 files. Your original files are never changed."
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        link = QLabel(f'<a href="{RELEASES_URL}">Releases and updates</a>')
        link.setOpenExternalLinks(True)
        layout.addWidget(link)

        self.update_status = QLabel()
        self.update_status.setObjectName("subtitle")
        self.update_status.setWordWrap(True)
        layout.addWidget(self.update_status)

        layout.addSpacing(6)
        self.details = QPlainTextEdit(support_details())
        self.details.setReadOnly(True)
        self.details.setFont(QFont("Menlo", 10))
        self.details.setFixedHeight(124)
        self.details.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.details)

        note = QLabel(
            "Only use CC Decrypter on files you own or have permission to decrypt."
        )
        note.setObjectName("subtitle")
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addSpacing(4)
        buttons = QHBoxLayout()
        copy = QPushButton("Copy details")
        copy.clicked.connect(self._copy)
        buttons.addWidget(copy)
        self.check_button = QPushButton("Check for updates")
        self.check_button.setToolTip("Asks github.com which version is newest")
        self.check_button.clicked.connect(self._check_for_updates)
        buttons.addWidget(self.check_button)
        buttons.addStretch(1)
        close = QPushButton("Close")
        close.setDefault(True)
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)

    def _copy(self) -> None:
        QApplication.clipboard().setText(self.details.toPlainText())

    def _check_for_updates(self) -> None:
        self.check_button.setEnabled(False)
        self.update_status.setText("Asking github.com…")
        threading.Thread(target=self._update_worker, daemon=True).start()

    def _update_worker(self) -> None:
        try:
            self.update_checked.emit(latest_release(), "")
        except Exception as exc:  # any network or parsing trouble
            self.update_checked.emit("", str(exc))

    def _show_update(self, latest: str, error: str) -> None:
        self.check_button.setEnabled(True)
        if error:
            self.update_status.setText(f"Could not check right now: {error}")
        elif not latest:
            self.update_status.setText("No published release was found.")
        elif version_tuple(latest) > version_tuple(__version__):
            self.update_status.setText(
                f'Version {latest} is available — <a href="{RELEASES_URL}">open the '
                "releases page</a>."
            )
            self.update_status.setOpenExternalLinks(True)
        else:
            self.update_status.setText(f"You are up to date ({__version__}).")


class LogWindow(QDialog):
    def __init__(self, parent: QWidget, lines) -> None:
        super().__init__(parent)
        self.setWindowTitle("CC Decrypter — Log")
        self.resize(680, 460)
        layout = QVBoxLayout(self)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Menlo", 11))
        self.text.setPlainText("\n".join(lines))
        layout.addWidget(self.text)
        self.scroll_to_end()

    def append(self, message: str) -> None:
        self.text.appendPlainText(message)
        self.scroll_to_end()

    def scroll_to_end(self) -> None:
        bar = self.text.verticalScrollBar()
        bar.setValue(bar.maximum())


class DecrypterWindow(QWidget):
    scan_done = Signal(object, object)
    batch_progress = Signal(int, int, str)
    batch_done = Signal(int, int, int, bool)
    logged = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CC Decrypter")
        self.resize(900, 780)
        self.setMinimumSize(640, 560)
        self._restore_geometry()

        self.videos: list[DraftVideo] = []
        self.busy = False
        self.log_lines: deque[str] = deque(maxlen=1000)
        self.log_window: LogWindow | None = None
        self.about_dialog: AboutDialog | None = None
        self.cancel_requested = threading.Event()

        self.sort_key, self.sort_descending = load_sort() or ("date", True)
        self.theme = load_theme()
        apply_color_scheme(self.theme)
        self.drafts_path, missing = resolve_drafts_folder(load_drafts_folder())
        self.output_dir = resolve_output_folder(load_output_folder())

        self._build()
        self.scan_done.connect(self._scan_finished)
        self.batch_progress.connect(self._batch_progressed)
        self.batch_done.connect(self._batch_finished)
        self.logged.connect(self._append_log)
        # only now will anything written actually reach the log
        self.write_log(support_details().replace("\n", " · "))

        if missing is not None:
            self.write_log(f"Saved drafts folder is gone: {missing}")
            QTimer.singleShot(0, lambda: self._report_missing_folder(missing))
        if self.drafts_path.is_dir():
            QTimer.singleShot(0, self.start_scan)
        else:
            self._set_status("working", "Drafts folder not found — click Choose… to pick it.")

    # ------------------------------------------------------------------ UI

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._outer_layout = outer
        centre = QHBoxLayout()
        centre.addStretch(1)
        column = QVBoxLayout()
        column.setContentsMargins(28, 26, 28, 20)
        column.setSpacing(10)
        holder = QWidget()
        holder.setLayout(column)
        holder.setMaximumWidth(CONTENT_WIDTH)
        holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        # the column takes the width first; the stretches only mop up what is left
        centre.addWidget(holder, 20)
        centre.addStretch(1)
        outer.addLayout(centre)

        header = QHBoxLayout()
        header.addStretch(1)
        header.addLayout(self._build_theme_switch())
        column.addLayout(header)

        title = QLabel("CC Decrypter")
        title_font = title.font()
        title_font.setPointSize(title_font.pointSize() + 9)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        column.addWidget(title)

        subtitle = QLabel("Videos from your CapCut drafts, decrypted into normal MP4 files.")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        column.addWidget(subtitle)

        column.addSpacing(18)
        column.addWidget(self._step_label("1 · DRAFTS FOLDER"))
        column.addWidget(self._build_folder_row())

        column.addSpacing(14)
        list_header = QHBoxLayout()
        list_header.addWidget(self._step_label("2 · PICK VIDEOS TO DECRYPT"))
        list_header.addStretch(1)
        list_header.addWidget(self._step_label("SORT"))
        self.sort_buttons: dict[str, QToolButton] = {}
        for label, key, _ in SORT_OPTIONS:
            button = QToolButton()
            button.setObjectName("sort")
            button.setText(label)
            button.clicked.connect(lambda _checked=False, key=key: self._on_sort(key))
            list_header.addWidget(button)
            self.sort_buttons[key] = button
        column.addLayout(list_header)

        self.list = QListWidget()
        self.list.setItemDelegate(VideoRow())
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.list.setUniformItemSizes(True)
        self.list.setMouseTracking(True)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list.setAlternatingRowColors(False)
        self.list.setFrameShape(QFrame.Shape.NoFrame)
        self.list.setSpacing(0)
        self.list.itemSelectionChanged.connect(self._selection_changed)
        column.addWidget(self.list, 1)

        column.addSpacing(6)
        progress_row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFormat("%v of %m")
        self.progress.setFixedHeight(18)
        self.progress.hide()
        progress_row.addWidget(self.progress, 1)
        self.cancel_button = QToolButton()
        self.cancel_button.setObjectName("link")
        self.cancel_button.setText("Cancel")
        self.cancel_button.clicked.connect(self._request_cancel)
        self.cancel_button.hide()
        progress_row.addWidget(self.cancel_button)
        column.addLayout(progress_row)

        self.counts = QLabel()
        self.counts.setObjectName("counts")
        self.counts.setAlignment(Qt.AlignmentFlag.AlignCenter)
        column.addWidget(self.counts)

        self.cta = QPushButton()
        self.cta.setObjectName("cta")
        self.cta.setMinimumHeight(48)
        self.cta.clicked.connect(self.start_batch)
        column.addWidget(self.cta)

        column.addSpacing(4)
        saved_row = QHBoxLayout()
        saved_row.setSpacing(6)
        saved_row.addStretch(1)
        saved_to = QLabel("Saved to")
        saved_to.setObjectName("subtitle")
        saved_row.addWidget(saved_to)
        self.output_label = ElidingPathLabel()
        self.output_label.setFont(QFont("Menlo", 11))
        # unlike the folder pill this one sits in a centred row, so it has to ask
        # for its width instead of taking whatever is left
        self.output_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.output_label.setMaximumWidth(340)
        self.output_label.clicked.connect(self._reveal_output)
        saved_row.addWidget(self.output_label)
        change = QToolButton()
        change.setObjectName("link")
        change.setText("Change…")
        change.clicked.connect(self._on_change_output)
        saved_row.addWidget(change)
        saved_row.addStretch(1)
        column.addLayout(saved_row)

        column.addSpacing(2)
        footer = QHBoxLayout()
        self.status = QLabel()
        footer.addWidget(self.status)
        footer.addStretch(1)
        about_button = QToolButton()
        about_button.setObjectName("link")
        about_button.setText(f"About · {__version__}")
        about_button.clicked.connect(self.show_about)
        footer.addWidget(about_button)
        log_button = QToolButton()
        log_button.setObjectName("link")
        log_button.setText("View log")
        log_button.clicked.connect(self.show_log)
        footer.addWidget(log_button)
        column.addLayout(footer)

        self._build_menu(outer)
        self.setStyleSheet(stylesheet(self.theme))
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._restyle)
        self._update_output_label()
        self._update_sort_buttons()
        self._selection_changed()
        self._set_status("neutral", "Starting…")

    def _build_menu(self, layout: QVBoxLayout) -> None:
        """macOS takes a parentless menu bar as the global one; elsewhere it has
        to sit in the window."""
        self.menu_bar = QMenuBar()
        self.actions_by_name = {}

        def action(menu, text, slot, shortcut=None, role=None):
            item = QAction(text, self)
            item.triggered.connect(slot)
            if shortcut is not None:
                item.setShortcut(QKeySequence(shortcut))
            if role is not None:
                item.setMenuRole(role)
            menu.addAction(item)
            self.actions_by_name[text] = item
            return item

        file_menu = self.menu_bar.addMenu("File")
        action(file_menu, "Rescan", self.start_scan, "Ctrl+R")
        action(file_menu, "Choose Drafts Folder…", self._on_choose_folder)
        action(file_menu, "Change Output Folder…", self._on_change_output)
        file_menu.addSeparator()
        action(file_menu, "Open Output Folder", self._reveal_output, "Ctrl+Shift+O")
        file_menu.addSeparator()
        action(file_menu, "Decrypt Selected", self.start_batch, "Ctrl+Return")

        edit_menu = self.menu_bar.addMenu("Edit")
        action(edit_menu, "Select All", self.list.selectAll, QKeySequence.StandardKey.SelectAll)
        action(edit_menu, "Clear Selection", self.list.clearSelection, "Ctrl+Shift+A")

        help_menu = self.menu_bar.addMenu("Help")
        action(help_menu, "View Log", self.show_log, "Ctrl+L")
        action(help_menu, "Check for Updates…", self.show_about)
        action(
            help_menu, "About CC Decrypter", self.show_about,
            role=QAction.MenuRole.AboutRole,
        )

        if sys.platform != "darwin":
            layout.setMenuBar(self.menu_bar)

    def show_about(self) -> None:
        if self.about_dialog is None:
            self.about_dialog = AboutDialog(self)
        self.about_dialog.show()
        self.about_dialog.raise_()
        self.about_dialog.activateWindow()

    def _step_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("step")
        return label

    def _build_theme_switch(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(0)
        self.theme_buttons: dict[str, QToolButton] = {}
        for theme, glyph, tip in (("light", "☀", "Light appearance"), ("dark", "☾", "Dark appearance")):
            button = QToolButton()
            button.setObjectName("segment")
            button.setProperty("side", theme)
            button.setText(glyph)
            button.setCheckable(True)
            button.setToolTip(tip)
            button.setFixedSize(38, 28)
            button.clicked.connect(lambda _checked=False, theme=theme: self._on_theme(theme))
            row.addWidget(button)
            self.theme_buttons[theme] = button
        self._update_theme_buttons()
        return row

    def _build_folder_row(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("pill")
        row = QHBoxLayout(frame)
        row.setContentsMargins(14, 7, 8, 7)
        row.setSpacing(4)
        self.folder_label = ElidingPathLabel()
        self.folder_label.setObjectName("path")
        self.folder_label.setFont(QFont("Menlo", 11))
        self.folder_label.setToolTip("Click to choose another folder")
        self.folder_label.clicked.connect(self._on_choose_folder)
        row.addWidget(self.folder_label, 1)
        choose = QToolButton()
        choose.setObjectName("link")
        choose.setText("Choose…")
        choose.clicked.connect(self._on_choose_folder)
        row.addWidget(choose)
        rescan = QToolButton()
        rescan.setObjectName("link")
        rescan.setText("Rescan")
        rescan.clicked.connect(self.start_scan)
        row.addWidget(rescan)
        self._update_folder_label()
        return frame

    def _update_folder_label(self) -> None:
        self.folder_label.setFullText(str(self.drafts_path))

    def _update_output_label(self) -> None:
        try:
            shown = str(Path("~") / self.output_dir.relative_to(Path.home()))
        except ValueError:
            shown = str(self.output_dir)
        self.output_label.setFullText(shown)
        self.output_label.setToolTip(f"{self.output_dir}\nClick to open this folder")

    def _reveal_output(self) -> None:
        if not self.output_dir.is_dir():
            self._set_status("neutral", "That folder appears when the first video is decrypted.")
            return
        reveal(self.output_dir)

    # --------------------------------------------------------------- list

    def _populate(self) -> None:
        chosen = {video.path for video in self.selected_videos()}
        self.list.blockSignals(True)
        self.list.clear()
        for video in sorted(
            self.videos, key=SORT_KEYS[self.sort_key], reverse=self.sort_descending
        ):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, video)
            item.setData(EXPORTED_ROLE, existing_export(video, self.output_dir) is not None)
            item.setText(video.path.name)  # gives keyboard type-ahead for free
            self.list.addItem(item)
            if video.path in chosen:
                item.setSelected(True)
        self.list.blockSignals(False)
        self._selection_changed()

    def selected_videos(self) -> list[DraftVideo]:
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.list.selectedItems()]

    def _selection_changed(self) -> None:
        picked = self.selected_videos()
        if self.videos:
            total = sum(video.size for video in picked)
            self.counts.setText(
                f"{len(picked)} of {len(self.videos)} videos selected · {human_size(total)}"
            )
        else:
            self.counts.setText("Nothing to decrypt yet.")

        if self.busy:
            self.cta.setEnabled(False)
            self.cta.setText("Working…")
        elif picked:
            self.cta.setEnabled(True)
            self.cta.setText(f"Decrypt {len(picked)} video{'s' if len(picked) != 1 else ''}")
        else:
            self.cta.setEnabled(False)
            self.cta.setText("Select videos to decrypt")

    # --------------------------------------------------------------- sort

    def _on_sort(self, key: str) -> None:
        if key == self.sort_key:
            self.sort_descending = not self.sort_descending
        else:
            self.sort_key = key
            self.sort_descending = next(
                default for _, option, default in SORT_OPTIONS if option == key
            )
        save_sort(self.sort_key, self.sort_descending)
        self._update_sort_buttons()
        self._populate()
        self.list.scrollToTop()

    def _update_sort_buttons(self) -> None:
        for label, key, _ in SORT_OPTIONS:
            active = key == self.sort_key
            arrow = ("▾" if self.sort_descending else "▴") if active else ""
            button = self.sort_buttons[key]
            button.setText(f"{label} {arrow}".strip())
            button.setProperty("active", "true" if active else "false")
            button.style().unpolish(button)
            button.style().polish(button)

    # -------------------------------------------------------------- theme

    def _on_theme(self, theme: str) -> None:
        if theme == self.theme:
            self._update_theme_buttons()
            return
        self.theme = theme
        save_theme(theme)
        apply_color_scheme(theme)
        self._restyle()

    def _restyle(self, *_args) -> None:
        self.setStyleSheet(stylesheet(self.theme))
        self._update_theme_buttons()
        self._update_sort_buttons()
        self.list.viewport().update()

    def _update_theme_buttons(self) -> None:
        current = self.theme or current_color_scheme()
        for theme, button in self.theme_buttons.items():
            button.setChecked(theme == current)

    # ------------------------------------------------------------ actions

    def _restore_geometry(self) -> None:
        saved = load_window_geometry()
        if saved is None:
            return
        x, y, width, height = saved
        self.resize(width, height)
        # only take the position back if it still lands on a screen
        for screen in QGuiApplication.screens():
            available = screen.availableGeometry()
            if available.contains(x + 40, y + 40):
                self.move(x, y)
                return

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        geometry = self.geometry()
        save_window_geometry(geometry.x(), geometry.y(), geometry.width(), geometry.height())
        super().closeEvent(event)

    def _report_missing_folder(self, missing: Path) -> None:
        if self.drafts_path.is_dir():
            detail = f"CC Decrypter is using this folder instead:\n{self.drafts_path}"
        else:
            detail = "Click Choose… at the top to pick the folder to scan."
        QMessageBox.information(
            self,
            "Saved drafts folder not found",
            f"The folder you picked last time is no longer there:\n{missing}\n\n{detail}",
        )

    def _on_choose_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Choose your CapCut drafts folder", str(self.drafts_path)
        )
        if not path:
            return
        self.drafts_path = Path(path)
        save_drafts_folder(self.drafts_path)
        self._update_folder_label()
        self.start_scan()

    def _on_change_output(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Choose where decrypted copies are saved", str(self.output_dir)
        )
        if not path:
            return
        self.output_dir = Path(path)
        save_output_folder(self.output_dir)
        self._update_output_label()
        self._populate()  # the "exported" marks belong to this folder

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self._selection_changed()

    def _set_status(self, kind: str, message: str) -> None:
        color = {"ok": GREEN, "working": AMBER, "error": RED}.get(kind, GREY)
        self.status.setText(f'<span style="color:{color}">●</span> {message}')

    # --------------------------------------------------------------- scan

    def start_scan(self) -> None:
        if self.busy:
            return
        if not self.drafts_path.is_dir():
            QMessageBox.critical(
                self, "Drafts folder not found", f"Could not find the folder:\n{self.drafts_path}"
            )
            return
        self._set_busy(True)
        self.videos = []
        self._populate()
        self._set_status("working", "Searching your CapCut drafts folder…")
        self.write_log(f"Searching {self.drafts_path} …")
        threading.Thread(target=self._scan_worker, args=(self.drafts_path,), daemon=True).start()

    def _scan_worker(self, folder: Path) -> None:
        try:
            self.scan_done.emit(find_protected_videos(folder), None)
        except Exception as exc:  # keep the UI usable no matter what
            self.scan_done.emit(None, exc)

    def _scan_finished(self, results, error) -> None:
        self._set_busy(False)
        if error is not None or results is None:
            self._set_status("error", "Something went wrong while searching — see the log.")
            self.write_log(f"ERROR while searching: {error}")
            return

        self.videos = [video for video in results if video.decryptable]
        unsupported = len(results) - len(self.videos)
        self._populate()
        self.list.scrollToTop()

        if self.videos:
            self._set_status("ok", f"Found {len(self.videos)} videos — click the ones to decrypt.")
            self.write_log(f"Found {len(self.videos)} video(s) you can decrypt.")
        else:
            self._set_status("neutral", "No protected videos were found in this folder.")
            self.write_log("No protected videos were found in this folder.")
        if unsupported:
            self.write_log(
                f"{unsupported} protected file(s) use an unsupported format and are not shown."
            )

    # -------------------------------------------------------------- batch

    def start_batch(self) -> None:
        videos = self.selected_videos()
        if self.busy or not videos:
            return

        done_already = [
            video for video in videos if existing_export(video, self.output_dir) is not None
        ]
        if done_already:
            choice = QMessageBox.question(
                self,
                "Already exported",
                f"{len(done_already)} of the {len(videos)} videos you picked are already in "
                "the output folder.\n\nSkip those, or decrypt them again as extra copies?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )
            if choice == QMessageBox.StandardButton.Cancel:
                return
            if choice == QMessageBox.StandardButton.Yes:
                videos = [video for video in videos if video not in done_already]
                if not videos:
                    self._set_status("ok", "Everything you picked was already exported.")
                    return

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(self, "Could not create output folder", str(exc))
            return

        self.cancel_requested.clear()
        self._set_busy(True)
        self.progress.setRange(0, len(videos))
        self.progress.setValue(0)
        self.progress.show()
        self.cancel_button.setText("Cancel")
        self.cancel_button.setEnabled(True)
        self.cancel_button.show()
        self._set_status("working", f"Decrypting {len(videos)} video(s)…")
        self.write_log(f"Decrypting {len(videos)} video(s) to {self.output_dir} …")
        threading.Thread(
            target=self._batch_worker, args=(videos, self.output_dir), daemon=True
        ).start()

    def _request_cancel(self) -> None:
        self.cancel_requested.set()
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Stopping…")
        self._set_status("working", "Finishing the current video, then stopping…")
        self.write_log("Cancel requested — stopping after the current video.")

    def _batch_progressed(self, index: int, total: int, name: str) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(index)
        self._set_status("working", f"Decrypting {index + 1} of {total} · {name}")

    def _batch_worker(self, videos: list[DraftVideo], output_dir: Path) -> None:
        taken: set[str] = set()
        done = failed = 0
        cancelled = False
        for index, video in enumerate(videos):
            if self.cancel_requested.is_set():
                cancelled = True
                break
            self.batch_progress.emit(index, len(videos), video.path.name)
            self.write_log(f"Decrypting: {video.path.name}")
            try:
                target = output_path_for(video, output_dir, taken)
                decode_file(video.path, target, self.write_log)
                done += 1
                self.write_log(f"Saved: {target}")
            except (DecodeError, OSError, ValueError) as exc:
                failed += 1
                self.write_log(f"ERROR: {video.path.name}: {exc}")
        self.batch_done.emit(done, failed, len(videos), cancelled)

    def _batch_finished(self, done: int, failed: int, total: int, cancelled: bool = False) -> None:
        self._set_busy(False)
        self.progress.hide()
        self.cancel_button.hide()
        self._populate()  # newly written files now show as exported
        if cancelled:
            self._set_status("neutral", f"Stopped: {done} of {total} decrypted.")
            self.write_log(f"Stopped after {done} of {total} video(s).")
            return
        if failed:
            self._set_status("error", f"Last run: {done} decrypted · {failed} failed.")
            QMessageBox.critical(
                self,
                "Some videos failed",
                f"Finished: {done} of {total} video(s) decrypted, {failed} failed.\n"
                "See View log for details.",
            )
        else:
            self._set_status("ok", f"Last run: {done} decrypted · 0 failed.")
            if done:
                box = QMessageBox(self)
                box.setWindowTitle("Done")
                box.setText(f"Decrypted {done} video(s).")
                box.setInformativeText(f"Saved to {self.output_dir}")
                show = box.addButton("Show in Finder", QMessageBox.ButtonRole.ActionRole)
                box.addButton(QMessageBox.StandardButton.Ok)
                box.exec()
                if box.clickedButton() is show:
                    self._reveal_output()

    # ----------------------------------------------------------- logging

    def write_log(self, message: str) -> None:
        self.logged.emit(message)

    def _append_log(self, message: str) -> None:
        self.log_lines.append(message)
        if self.log_window is not None and self.log_window.isVisible():
            self.log_window.append(message)

    def show_log(self) -> None:
        if self.log_window is None:
            self.log_window = LogWindow(self, self.log_lines)
        else:
            self.log_window.text.setPlainText("\n".join(self.log_lines))
            self.log_window.scroll_to_end()
        self.log_window.show()
        self.log_window.raise_()
        self.log_window.activateWindow()


def build_palette(theme: str) -> QPalette:
    """A full palette for a pinned theme, so the look does not depend on the
    platform honouring the colour-scheme hint."""
    t = tokens(theme)
    palette = QPalette()
    window = QColor(t["window"])
    base = QColor(t["list_bg"])
    text = QColor(t["text"])
    for role, colour in (
        (QPalette.ColorRole.Window, window),
        (QPalette.ColorRole.WindowText, text),
        (QPalette.ColorRole.Base, base),
        (QPalette.ColorRole.AlternateBase, QColor(t["surface"])),
        (QPalette.ColorRole.Text, text),
        (QPalette.ColorRole.Button, QColor(t["surface"])),
        (QPalette.ColorRole.ButtonText, text),
        (QPalette.ColorRole.ToolTipBase, base),
        (QPalette.ColorRole.ToolTipText, text),
        (QPalette.ColorRole.PlaceholderText, QColor(GREY)),
        (QPalette.ColorRole.Mid, QColor(GREY)),
        (QPalette.ColorRole.Link, QColor(t["accent"])),
        (QPalette.ColorRole.LinkVisited, QColor(t["accent"])),
        (QPalette.ColorRole.Highlight, QColor(t["accent"])),
        (QPalette.ColorRole.HighlightedText, QColor("white")),
    ):
        palette.setColor(role, colour)
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(t["disabled_fg"])
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(t["disabled_fg"])
    )
    return palette


def apply_color_scheme(theme: str | None) -> None:
    """Force light or dark, or follow the system when theme is None."""
    hints = QGuiApplication.styleHints()
    if hasattr(hints, "setColorScheme"):
        hints.setColorScheme(
            {
                "light": Qt.ColorScheme.Light,
                "dark": Qt.ColorScheme.Dark,
            }.get(theme, Qt.ColorScheme.Unknown)
        )
    app = QApplication.instance()
    if app is None:
        return
    app.setPalette(build_palette(theme) if theme else app.style().standardPalette())


def current_color_scheme() -> str:
    hints = QGuiApplication.styleHints()
    scheme = getattr(hints, "colorScheme", None)
    if scheme is None:
        return "light"
    return "dark" if scheme() == Qt.ColorScheme.Dark else "light"


def main() -> None:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("CC Decrypter")
    window = DecrypterWindow()
    window.show()
    app.exec()
