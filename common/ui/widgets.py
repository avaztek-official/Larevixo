"""Small reusable Qt layout and widget helpers."""
from __future__ import annotations

import re

from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter, QTextCharFormat, QSyntaxHighlighter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QCompleter, QFrame, QHBoxLayout, QLabel,
    QListView, QTableWidget, QHeaderView, QPushButton, QVBoxLayout,
)


_ANSI_ESCAPE = re.compile(
    r"\x1B(?:"
    r"\[[0-?]*[ -/]*[@-~]"  # CSI sequences, including colors (SGR)
    r"|\][^\x07\x1B]*(?:\x07|\x1B\\)"  # OSC sequences
    r"|[PX^_].*?\x1B\\"  # DCS, SOS, PM, and APC strings
    r"|[@-_]"  # Two-character ESC sequences
    r")",
    re.DOTALL,
)


def strip_ansi(text: str) -> str:
    """Remove terminal control sequences unsupported by the plain-text UI."""
    return _ANSI_ESCAPE.sub("", text)


def hbox(*widgets, gap=10):
    layout = QHBoxLayout()
    layout.setSpacing(gap)
    layout.setContentsMargins(0, 0, 0, 0)
    for widget in widgets:
        layout.addWidget(widget)
    return layout


def column(*widgets, gap=13):
    layout = QVBoxLayout()
    layout.setSpacing(gap)
    layout.setContentsMargins(0, 0, 0, 0)
    for widget in widgets:
        layout.addWidget(widget)
    return layout


def lucide_icon(name, color, base):
    svg = (base / "assets" / "lucide-source" / f"{name}.svg").read_bytes()
    svg = svg.replace(b"currentColor", color.encode())
    renderer = QSvgRenderer(QByteArray(svg))
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def btn(text, callback, translate, kind="secondary", icon_name=None):
    button = QPushButton(translate(text))
    button.setProperty("kind", kind)
    button.setProperty("iconName", icon_name or "")
    if icon_name:
        button.setIconSize(QSize(16, 16))
    button.setFixedHeight(46 if kind == "nav" else 42)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.clicked.connect(callback)
    return button


def label(text, translate, role="muted"):
    widget = QLabel(translate(text))
    widget.setProperty("role", role)
    widget.setWordWrap(True)
    return widget


def card(title, translate, subtitle=None):
    frame = QFrame()
    frame.setObjectName("panel")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(19, 16, 19, 18)
    layout.setSpacing(11)
    layout.addWidget(label(title, translate, "cardTitle"))
    if subtitle:
        layout.addWidget(label(subtitle, translate))
    return frame, layout


def page(title, subtitle, translate):
    from PySide6.QtWidgets import QWidget

    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(3, 0, 3, 1)
    layout.setSpacing(15)
    layout.addWidget(label(title, translate, "pageTitle"))
    layout.addWidget(label(subtitle, translate))
    return container, layout


def editable_table(columns, translate):
    table = QTableWidget(0, len(columns))
    table.setHorizontalHeaderLabels([translate(column) for column in columns])
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.verticalHeader().hide()
    table.setAlternatingRowColors(False)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    return table


def configure_searchable_combo(combo, event_filter_owner=None, register=None):
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    completer = QCompleter(combo.model(), combo)
    completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    completer.setFilterMode(Qt.MatchFlag.MatchContains)
    completer.setPopup(QListView(combo))
    completer.popup().setObjectName("searchableComboCompleter")
    combo.setCompleter(completer)
    if event_filter_owner is not None:
        combo.lineEdit().installEventFilter(event_filter_owner)
    if register is not None:
        register(combo)
    return combo


class AnchoredComboBox(QComboBox):
    def showPopup(self):
        super().showPopup()
        popup = self.view().window()
        screen = self.screen()
        if screen is None:
            return
        available = screen.availableGeometry()
        field_top = self.mapToGlobal(QPoint(0, 0))
        below_y = self.mapToGlobal(QPoint(0, self.height())).y()
        popup_geometry = popup.geometry()
        width = min(popup_geometry.width(), available.width())
        space_below = max(0, available.bottom() - below_y + 1)
        space_above = max(0, field_top.y() - available.top())
        if popup_geometry.height() <= space_below or space_below >= space_above:
            y = below_y
            height = min(popup_geometry.height(), space_below)
        else:
            height = min(popup_geometry.height(), space_above)
            # Qt's popup window frame extends one logical pixel beyond its client geometry.
            y = field_top.y() - height - 1
        x = min(max(field_top.x(), available.left()), available.right() - width + 1)
        popup.setGeometry(x, y, width, max(1, height))


class LogHighlighter(QSyntaxHighlighter):
    """Color complete log lines by severity while keeping streamed output intact."""

    _PATTERNS = (
        ("error", re.compile(r"\b(error|critical|fatal|exception|failed|failure)\b", re.IGNORECASE)),
        ("warning", re.compile(r"\b(warn|warning)\b", re.IGNORECASE)),
        ("success", re.compile(r"\b(success|successful|completed|created|installed|passed|done)\b", re.IGNORECASE)),
        ("info", re.compile(r"\b(info|notice|debug)\b|ℹ", re.IGNORECASE)),
    )
    _COLORS = {
        "light": {"error": "#b32612", "warning": "#a85d00", "success": "#18733a", "info": "#1769aa"},
        "dark": {"error": "#ff796c", "warning": "#ffc266", "success": "#68d391", "info": "#73bfff"},
    }

    def __init__(self, document):
        super().__init__(document)
        self.theme = "light"

    def set_theme(self, theme):
        self.theme = theme
        self.rehighlight()

    def highlightBlock(self, text):
        for level, pattern in self._PATTERNS:
            if pattern.search(text):
                fmt = QTextCharFormat()
                fmt.setForeground(QColor(self._COLORS[self.theme][level]))
                self.setFormat(0, len(text), fmt)
                return
