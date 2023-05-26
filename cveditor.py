import re

from PyQt6.QtWidgets import QApplication, QMainWindow, QPlainTextEdit
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QColor


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
        self._highlighter = CvSyntaxHighlighter(self)
        self._highlighter.setDocument(self.document())

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
    DATE = QTextCharFormat()
    SECTION = QTextCharFormat()
    UNKNOWN = QTextCharFormat()

    def __init__(self, parent):
        super().__init__(parent)
        self.update_format(self.DEFAULT)
        self.update_format(self.KEYWORD, foreground="#1E90FF", bold=True)  # dodger blue
        self.update_format(self.DATE, foreground="#DA70D6", bold=True)  # orchid
        self.update_format(self.SECTION, foreground="#9400D3", bold=True)  # dark orchid
        self.update_format(self.UNKNOWN, foreground="#FFA500")  # orange

    @staticmethod
    def update_format(text_format: QTextCharFormat, foreground="#000000", bold=False):
        text_format.setForeground(QColor(foreground))
        text_format.setFontWeight(700 if bold else 400)

    def highlightBlock(self, text):
        for pattern, name in self._PATTERNS.items():
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                span = match.span()
                if name in ("keyword-text", "bullet-text"):
                    self.setFormat(*match.span(1), self.KEYWORD)
                    self.setFormat(*match.span(2), self.DEFAULT)
                elif name == "date":
                    self.setFormat(*match.span(1), self.DATE)
                elif name == "section-text":
                    self.setFormat(*span, self.SECTION)
                elif name == "unknown":
                    self.setFormat(*span, self.UNKNOWN)
                else:
                    raise ValueError(name)


def _test():
    app = QApplication([])
    window = QMainWindow()
    editor = CvEditor(window)
    window.setCentralWidget(editor)

    editor.setFont(QFont("Consolas", 10))
    editor.document().setDocumentMargin(10)
    with open("tests/sample1.txt", encoding="utf-8") as f:
        editor.setPlainText(f.read())

    window.setGeometry(200, 100, 800, 660)
    window.show()
    app.exec()


if __name__ == "__main__":
    _test()
