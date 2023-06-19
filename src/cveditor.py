import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPlainTextEdit, QApplication
from PyQt6.QtGui import (
    QAction,
    QSyntaxHighlighter,
    QTextCharFormat,
    QColor,
)


KEYWORDS = sorted(
    [
        "name",
        "email",
        "phone",
        "address",
        "website",
        "loc",
        r"start\s+date",
        r"end\s+date",
        "school",
        "degree",
        "major",
        "minor",
        "gpa",
        "rank",
        "courses",
        "role",
        "org",
        r"hours\s+per\s+week",
        r"weeks\s+per\s+year",
        "test",
        "score",
        r"test\s+date",
        "award",
        r"award\s+date",
        r"skillset\s+name",
        "skills",
    ],
    key=len,
    reverse=True,
)

_DATE_KEYWORDS = [kw for kw in KEYWORDS if kw.endswith("date")]


class CvEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighter = CvSyntaxHighlighter(self)
        self.highlighter.setDocument(self.document())

        self.undo_action = self._create_actions("&Undo", "Ctrl+z")
        self.undo_action.triggered.connect(self.undo)
        self.redo_action = self._create_actions("&Redo", "Ctrl+y")
        self.redo_action.triggered.connect(self.redo)
        self.cut_action = self._create_actions("Cu&t", "Ctrl+x")
        self.cut_action.triggered.connect(self.cut)
        self.copy_action = self._create_actions("&Copy", "Ctrl+c")
        self.copy_action.triggered.connect(self.copy)
        self.paste_action = self._create_actions("&Paste", "Ctrl+v")
        self.paste_action.triggered.connect(self.paste)
        self.selectall_action = self._create_actions("Select &All", "Ctrl+a")
        self.selectall_action.triggered.connect(self.selectAll)

        # TODO
        self.find_action = self._create_actions("&Find", "Ctrl+f")
        self.find_action.setDisabled(True)
        self.replace_action = self._create_actions("&Replace", "Ctrl+h")
        self.replace_action.setDisabled(True)

        # Connect to slots
        self.undoAvailable.connect(self.undo_action.setEnabled)
        self.redoAvailable.connect(self.redo_action.setEnabled)
        self.selectionChanged.connect(self._on_selection_change)
        self._clipboard = QApplication.clipboard()
        self._clipboard.changed.connect(self._on_clipboard_change)

        # Initialize
        self.undo_action.setDisabled(True)
        self.redo_action.setDisabled(True)
        self.cut_action.setDisabled(True)
        self.copy_action.setDisabled(True)
        self._on_clipboard_change()

    def _create_actions(self, text, shortcut) -> QAction:
        action = QAction(text, self)
        action.setShortcut(shortcut)
        action.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
        return action

    def _on_selection_change(self):
        state = bool(self.get_selected())
        self.cut_action.setEnabled(state)
        self.copy_action.setEnabled(state)

    def _on_clipboard_change(self):
        state = bool(self._clipboard.text())
        self.paste_action.setEnabled(state)

    def insert(self, text: str):
        self.insertPlainText(text)
        self.ensureCursorVisible()

    def get_selected(self):
        return self.textCursor().selectedText()


class CvSyntaxHighlighter(QSyntaxHighlighter):
    _PATTERNS = {
        # in order of increasing priority
        # - line of unknown syntax
        r"^(.+)$": "unknown",
        # - keyword followed by text
        rf"^\s*((?:{'|'.join(KEYWORDS)})\s*[:：])(.*)$": "keyword-text",
        # - date keyword followed by date
        rf"^\s*(?:{'|'.join(_DATE_KEYWORDS)})\s*[:：]"
        rf"\s*(\d{{4}}(?:([-./])([01]?[0-9])(?:\2([0-3]?[0-9]))?)?)\s*$": "date",
        # - bullet point followed by text
        r"^\s*([-•])\s*(.*)$": "bullet-text",
        # - section symbol `#` followed by heading text
        r"^\s*#\s*(.+)$": "section-text",
    }

    DEFAULT = QTextCharFormat()
    KEYWORD = QTextCharFormat()
    BULLET = QTextCharFormat()
    DATE = QTextCharFormat()
    SECTION = QTextCharFormat()
    UNKNOWN = QTextCharFormat()

    @staticmethod
    def update_format(
        text_format: QTextCharFormat,
        foreground=None,
        background=None,
        bold=None,
        italic=None,
        underline=None,
    ):
        if foreground is not None:
            text_format.setForeground(QColor(foreground))
        if background is not None:
            text_format.setBackground(QColor(background))
        if bold is not None:
            text_format.setFontWeight(700 if bold else 400)
        if italic is not None:
            text_format.setFontItalic(italic)
        if underline is not None:
            text_format.setFontUnderline(underline)

    def highlightBlock(self, text):
        for pattern, name in self._PATTERNS.items():
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                if name == "keyword-text":
                    self.setFormat(*match.span(1), self.KEYWORD)
                    self.setFormat(*match.span(2), self.DEFAULT)
                elif name == "bullet-text":
                    self.setFormat(*match.span(1), self.BULLET)
                    self.setFormat(*match.span(2), self.DEFAULT)
                elif name == "date":
                    self.setFormat(*match.span(1), self.DATE)
                elif name == "section-text":
                    self.setFormat(*match.span(), self.SECTION)
                elif name == "unknown":
                    self.setFormat(*match.span(), self.UNKNOWN)
                else:
                    raise ValueError(name)
