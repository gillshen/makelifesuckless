import re

from PyQt6.QtWidgets import QPlainTextEdit
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor


KEY_WORDS = sorted(
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

_DATE_KWS = [kw for kw in KEY_WORDS if kw.endswith("date")]


class CvEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighter = CvSyntaxHighlighter(self)
        self.highlighter.setDocument(self.document())

    def insert(self, text: str):
        self.insertPlainText(text)
        self.ensureCursorVisible()

    def get_selected(self):
        return self.textCursor().selectedText()


class CvSyntaxHighlighter(QSyntaxHighlighter):
    _PATTERNS = {
        # in order of increasing priority
        r"^(.+)$": "unknown",
        rf"^\s*((?:{'|'.join(KEY_WORDS)})\s*[:：])(.*)$": "keyword-text",
        rf"^\s*(?:{'|'.join(_DATE_KWS)})\s*[:：]\s*(\d{{4}}(?:([-./])([01]?[0-9])(?:\2([0-3]?[0-9]))?)?)\s*$": "date",
        r"^\s*([-•])\s*(.*)$": "bullet-text",
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
