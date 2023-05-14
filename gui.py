import sys
import os
import traceback

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence, QFont, QCloseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QSizePolicy,
    QMenu,
    QPlainTextEdit,
    QFrame,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QFontComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QLineEdit,
    QFileDialog,
    QMessageBox,
)

from render import Settings
from txtparse import SmartDate

APP_TITLE = "Curriculum Victim"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._filepath = ""
        self.menubar = self.menuBar()

        # Main widget
        central_widget = QSplitter(self)
        self.setCentralWidget(central_widget)

        # Left panel
        editor_panel = QSplitter(Qt.Orientation.Vertical, self)
        central_widget.addWidget(editor_panel)

        # Editor
        self.editor = QPlainTextEdit(self)
        self.editor.setFrameShape(QFrame.Shape.NoFrame)
        self.document = self.editor.document()
        self.document.setDocumentMargin(6)
        self.editor.textChanged.connect(self._on_editor_change)
        editor_panel.addWidget(self.editor)

        # Console
        self.console = QPlainTextEdit(self)
        self.console.setFrameShape(QFrame.Shape.NoFrame)
        editor_panel.addWidget(self.console)

        # Right panel
        control_panel = QFrame(self)
        central_widget.addWidget(control_panel)
        control_panel_layout = QVBoxLayout()
        control_panel.setLayout(control_panel_layout)

        settings_area = QScrollArea(self)
        settings_area.setFrameShape(QFrame.Shape.NoFrame)
        control_panel_layout.addWidget(settings_area)

        self.settings_frame = SettingsFrame(self)
        settings_area.setWidget(self.settings_frame)
        settings_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        settings_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        settings_area.setWidgetResizable(True)

        control_panel_layout.addSpacing(10)

        run_button = QPushButton("Run")
        run_button.clicked.connect(self.run_latex)
        control_panel_layout.addWidget(run_button)
        run_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        # Create menu actions
        self._create_menu()

        # UI preferences
        self.editor.setFont(QFont("Consolas", pointSize=12))  # TODO preferences
        # TODO line wrap

        # Set window properties
        self.setGeometry(200, 100, 1000, 640)
        central_widget.setSizes([680, 320])
        editor_panel.setSizes([450, 150])

        self.new_file()
        self.show()

    def _create_menu(self):
        # File menu
        file_menu = QMenu("&File", self)

        new_action = QAction("&New", self)
        new_action.triggered.connect(self.new_file)
        new_action.setShortcut(QKeySequence("Ctrl+n"))
        file_menu.addAction(new_action)

        open_action = QAction("&Open...", self)
        open_action.triggered.connect(self.open_file)
        open_action.setShortcut(QKeySequence("Ctrl+o"))
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("&Save", self)
        save_action.triggered.connect(self.save_file)
        save_action.setShortcut(QKeySequence("Ctrl+s"))
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.triggered.connect(self.save_file_as)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+s"))
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.triggered.connect(self.close)
        quit_action.setShortcut(QKeySequence("Ctrl+q"))
        file_menu.addAction(quit_action)

        self.menubar.addMenu(file_menu)

        # Edit menu
        edit_menu = QMenu("&Edit", self)

        undo_action = QAction("&Undo", self)
        undo_action.triggered.connect(self.editor.undo)
        undo_action.setShortcut("Ctrl+z")
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Redo", self)
        redo_action.triggered.connect(self.editor.redo)
        redo_action.setShortcut("Ctrl+y")
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction("Cu&t", self)
        cut_action.triggered.connect(self.editor.cut)
        cut_action.setShortcut("Ctrl+x")
        edit_menu.addAction(cut_action)

        copy_action = QAction("&Copy", self)
        copy_action.triggered.connect(self.editor.copy)
        copy_action.setShortcut("Ctrl+c")
        edit_menu.addAction(copy_action)

        paste_action = QAction("&Paste", self)
        paste_action.triggered.connect(self.editor.paste)
        paste_action.setShortcut("Ctrl+v")
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        find_action = QAction("&Find", self)
        # TODO
        find_action.triggered.connect(lambda: print("editor.find"))
        find_action.setDisabled(True)
        find_action.setShortcut(QKeySequence("Ctrl+f"))
        edit_menu.addAction(find_action)

        replace_action = QAction("&Replace", self)
        # TODO
        replace_action.triggered.connect(lambda: print("editor.replace"))
        replace_action.setDisabled(True)
        replace_action.setShortcut(QKeySequence("Ctrl+r"))
        edit_menu.addAction(replace_action)

        edit_menu.addSeparator()

        toggle_wrap_action = QAction("Wrap Lines", self)
        toggle_wrap_action.triggered.connect(self.toggle_wrap)
        toggle_wrap_action.setShortcut(QKeySequence("Alt+z"))
        toggle_wrap_action.setCheckable(True)
        toggle_wrap_action.setChecked(True)
        edit_menu.addAction(toggle_wrap_action)

        preferences_action = QAction("&Preferences...", self)
        preferences_action.triggered.connect(self.launch_pref_dialog)
        preferences_action.setShortcut(QKeySequence("Ctrl+,"))
        edit_menu.addAction(preferences_action)

        self.menubar.addMenu(edit_menu)

        # View menu
        settings_menu = QMenu("La&TeX", self)

        import_settings_action = QAction("&Import Settings...", self)
        import_settings_action.triggered.connect(self.import_settings)
        import_settings_action.setShortcut(QKeySequence("Ctrl+i"))
        settings_menu.addAction(import_settings_action)

        export_settings_action = QAction("&Export Settings...", self)
        export_settings_action.triggered.connect(self.export_settings)
        export_settings_action.setShortcut(QKeySequence("Ctrl+e"))
        settings_menu.addAction(export_settings_action)

        settings_menu.addSeparator()

        restore_default_action = QAction("Restore &Default", self)
        restore_default_action.triggered.connect(self.restore_default)
        restore_default_action.setShortcut(QKeySequence("Ctrl+Shift+d"))
        settings_menu.addAction(restore_default_action)

        self.menubar.addMenu(settings_menu)

    def closeEvent(self, event: QCloseEvent):
        # Ask user to handle unsaved change if any
        if self.isWindowModified() and not _ask_yesno(
            parent=self,
            default_yes=False,
            text=(
                "Your document has unsaved changes.\n"
                "Discard the changes and close the program?"
            ),
        ):
            event.ignore()
        else:
            event.accept()

    def get_settings(self) -> Settings:
        return self.settings_frame.get_settings()

    def handle_exc(self, e: Exception):
        self.log(traceback.format_exc())
        _show_error(parent=self, text=f"Oops, something went wrong.\n{e}")

    def log(self, message: str):
        self.console.setPlainText(message)

    def run_latex(self):
        # TODO
        from pprint import pformat
        from dataclasses import asdict

        self.log(pformat(asdict(self.get_settings())))

    def update_filepath(self):
        if self._filepath:
            filename = os.path.basename(self._filepath)
        else:
            filename = "<untitled>"
        self.setWindowTitle(f"{filename}[*] - {APP_TITLE}")
        self.setWindowFilePath(self._filepath)

    def _on_editor_change(self):
        self.setWindowModified(self.document.isModified())

    def new_file(self):
        self.editor.setPlainText("")
        self._filepath = ""
        self.update_filepath()

    def open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, caption="Open File", directory="", filter="TXT Files (*.txt)"
        )
        if not filepath:
            return
        try:
            with open(filepath, encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            self.handle_exc(e)
        else:
            self.editor.setPlainText(text)
            self.setWindowModified(False)
            self._filepath = filepath
            self.update_filepath()

    def _save_file(self, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.editor.toPlainText())
        self.setWindowModified(False)

    def save_file(self):
        if not self._filepath:
            self.save_file_as()
            return
        try:
            self._save_file(self._filepath)
        except Exception as e:
            self.handle_exc(e)

    def save_file_as(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, caption="Save File", directory="", filter="TXT Files (*.txt)"
        )
        if not filepath:
            return
        try:
            self._save_file(filepath=filepath)
        except Exception as e:
            self.handle_exc(e)
        else:
            self._filepath = filepath
            self.update_filepath()

    def toggle_wrap(self, state):
        if state:
            wrap_mode = QPlainTextEdit.LineWrapMode.WidgetWidth
        else:
            wrap_mode = QPlainTextEdit.LineWrapMode.NoWrap
        self.editor.setLineWrapMode(wrap_mode)

    def launch_pref_dialog(self):
        # TODO
        print("open preferences dialog")

    def import_settings(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            caption="Import Settings",
            directory="settings",
            filter="JSON Files (*.json)",
        )
        if not filepath:
            return
        # TODO
        print(filepath)

    def export_settings(self):
        # TODO
        print("export settings")

    def restore_default(self):
        # TODO
        print("restore default settings")


class SettingsFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        self.setLayout(layout)
        space_after_group = 15
        space_within_group = 5
        space_after_separator = 10

        # text font
        layout.addWidget(SettingsHeading("Text Font"))
        self.text_font_selector = QFontComboBox(self)
        layout.addWidget(self.text_font_selector)
        self.text_size_selector = QSpinBox(self, minimum=8, maximum=14, suffix=" pt")
        layout.addWidget(self.text_size_selector)
        layout.addSpacing(space_after_group)

        # heading font
        layout.addWidget(SettingsHeading("Heading Font"))
        self.heading_font_selector = QFontComboBox(self)
        layout.addWidget(self.heading_font_selector)
        self.heading_size_selector = LatexFontSizeSelector(self)
        layout.addWidget(self.heading_size_selector)
        layout.addSpacing(space_after_group)

        # title font
        layout.addWidget(SettingsHeading("Title Font"))
        self.title_font_selector = QFontComboBox(self)
        layout.addWidget(self.title_font_selector)
        self.title_size_selector = LatexFontSizeSelector(self)
        layout.addWidget(self.title_size_selector)
        layout.addSpacing(space_after_group)

        # font features
        layout.addWidget(SettingsHeading("Number Style"))
        self.proportional_numbers_check = QCheckBox("Proportional", self)
        layout.addWidget(self.proportional_numbers_check)
        self.oldstyle_numbers_check = QCheckBox("Old Style", self)
        layout.addWidget(self.oldstyle_numbers_check)
        layout.addSpacing(space_after_group)

        layout.addWidget(Separator(self))
        layout.addSpacing(space_after_separator)

        # paper
        layout.addWidget(SettingsHeading("Paper"))
        self.paper_selector = LatexPaperSelector(self)
        layout.addWidget(self.paper_selector)
        layout.addSpacing(space_after_group)

        # margins
        layout.addWidget(SettingsHeading("Margins"))
        margins_grid = QFrame(self)
        layout.addWidget(margins_grid)
        margins_grid_layout = QGridLayout()
        margins_grid.setLayout(margins_grid_layout)
        margins_grid_layout.setColumnStretch(0, 0)
        margins_grid_layout.setColumnStretch(1, 1)
        margins_grid_layout.setContentsMargins(0, 5, 0, 5)

        self.margin_selectors = {}
        for row, pos in enumerate(["top", "left", "right", "bottom"]):
            margins_grid_layout.addWidget(QLabel(pos.title()), row, 0)
            w = self.margin_selectors[pos] = QDoubleSpinBox(self, suffix=" in")
            w.setSingleStep(0.1)
            w.setMaximum(3.0)
            margins_grid_layout.addWidget(w, row, 1)
        layout.addSpacing(space_after_group)

        layout.addWidget(SettingsHeading("Line Height"))
        self.line_spread_selector = QDoubleSpinBox(self)
        self.line_spread_selector.setSingleStep(0.1)
        layout.addWidget(self.line_spread_selector)
        layout.addSpacing(space_within_group)

        layout.addWidget(SettingsHeading("Space Between Paragraphs"))
        self.paragraph_skip_selector = QSpinBox(self, suffix=" pt")
        layout.addWidget(self.paragraph_skip_selector)
        layout.addSpacing(space_within_group)

        layout.addWidget(SettingsHeading("Space Between Entries"))
        self.entry_skip_selector = QSpinBox(self, suffix=" pt")
        layout.addWidget(self.entry_skip_selector)
        layout.addSpacing(space_after_group)

        layout.addWidget(Separator(self))
        layout.addSpacing(space_after_separator)

        # headings
        layout.addWidget(SettingsHeading("Section Title Style"))
        self.bold_headings_check = QCheckBox("Bold", self)
        layout.addWidget(self.bold_headings_check)
        self.all_cap_headings_check = QCheckBox("All Caps", self)
        layout.addWidget(self.all_cap_headings_check)
        layout.addSpacing(space_after_group)

        # activities section title
        layout.addWidget(SettingsHeading("Default Activities Section Title"))
        self.default_activities_title_edit = QLineEdit(self)
        layout.addWidget(self.default_activities_title_edit)
        layout.addSpacing(space_within_group)

        # awards section title
        layout.addWidget(SettingsHeading("Awards Section Title"))
        self.awards_title_edit = QLineEdit(self)
        layout.addWidget(self.awards_title_edit)
        layout.addSpacing(space_within_group)

        # skills section title
        layout.addWidget(SettingsHeading("Skills Section Title"))
        self.skills_title_edit = QLineEdit(self)
        layout.addWidget(self.skills_title_edit)
        layout.addSpacing(space_after_group)

        layout.addWidget(Separator(self))
        layout.addSpacing(space_after_separator)

        # date format
        layout.addWidget(SettingsHeading("Date Format"))
        self.date_style_selector = DateFormatSelector(self)
        layout.addWidget(self.date_style_selector)
        layout.addSpacing(space_after_group)

        layout.addWidget(Separator(self))
        layout.addSpacing(space_after_separator)

        # url appearance
        self.url_follows_text_check = QCheckBox("Use Text Font for URLs", self)
        layout.addWidget(self.url_follows_text_check)
        self.color_links_check = QCheckBox("Enable URL Color", self)
        layout.addWidget(self.color_links_check)
        layout.addSpacing(space_after_group)

        layout.addWidget(SettingsHeading("URL Color"))
        self.url_color_selector = LatexColorSelector(self)
        layout.addWidget(self.url_color_selector)
        layout.addSpacing(space_after_group)

        # handle events
        def _update_url_color_selector():
            selectable = self.color_links_check.isChecked()
            self.url_color_selector.setEnabled(selectable)

        self.color_links_check.stateChanged.connect(_update_url_color_selector)

    def get_settings(self) -> Settings:
        s = Settings()

        s.main_font = self.text_font_selector.currentText()
        s.font_size_in_point = self.text_size_selector.value()

        s.heading_font = self.heading_font_selector.currentText()
        s.heading_relative_size = self.heading_size_selector.get_command()

        s.title_font = self.title_font_selector.currentText()
        s.title_relative_size = self.title_size_selector.get_command()

        s.proportional_numbers = self.proportional_numbers_check.isChecked()
        s.old_style_numbers = self.oldstyle_numbers_check.isChecked()

        s.paper = self.paper_selector.get_paper()

        s.top_margin_in_inch = self.margin_selectors["top"].value()
        s.bottom_margin_in_inch = self.margin_selectors["bottom"].value()
        s.left_margin_in_inch = self.margin_selectors["left"].value()
        s.right_margin_in_inch = self.margin_selectors["right"].value()

        s.line_spread = self.line_spread_selector.value()
        s.paragraph_skip_in_pt = self.paragraph_skip_selector.value()
        s.entry_skip_in_pt = self.entry_skip_selector.value()

        s.bold_headings = self.bold_headings_check.isChecked()
        s.all_cap_headings = self.all_cap_headings_check.isChecked()

        s.default_activities_section_title = self.default_activities_title_edit.text()
        s.awards_section_title = self.awards_title_edit.text()
        s.skills_section_title = self.skills_title_edit.text()

        s.date_style = self.date_style_selector.get_style()

        s.url_font_follows_text = self.url_follows_text_check.isChecked()
        s.color_links = self.color_links_check.isChecked()
        s.url_color = self.url_color_selector.get_color()

        return s

    def load_settings(self, s: Settings):
        self.text_font_selector.setCurrentFont(QFont(s.main_font))
        self.text_size_selector.setValue(s.font_size_in_point)

        self.heading_font_selector.setCurrentFont(QFont(s.heading_font))
        self.heading_size_selector.set_from_command(s.heading_relative_size)

        self.title_font_selector.setCurrentFont(QFont(s.title_font))
        self.title_size_selector.set_from_command(s.title_relative_size)

        self.proportional_numbers_check.setChecked(s.proportional_numbers)
        self.oldstyle_numbers_check.setChecked(s.old_style_numbers)

        self.paper_selector.setCurrentText(s.paper)

        self.margin_selectors["top"].setValue(s.top_margin_in_inch)
        self.margin_selectors["bottom"].setValue(s.bottom_margin_in_inch)
        self.margin_selectors["left"].setValue(s.left_margin_in_inch)
        self.margin_selectors["right"].setValue(s.right_margin_in_inch)

        self.line_spread_selector.setValue(s.line_spread)
        self.paragraph_skip_selector.setValue(s.paragraph_skip_in_pt)
        self.entry_skip_selector.setValue(s.entry_skip_in_pt)

        self.bold_headings_check.setChecked(s.bold_headings)
        self.all_cap_headings_check.setChecked(s.all_cap_headings)

        self.default_activities_title_edit.setText(s.default_activities_section_title)
        self.awards_title_edit.setText(s.awards_section_title)
        self.skills_title_edit.setText(s.skills_section_title)

        self.date_style_selector.set_from_style(s.date_style)
        self.url_follows_text_check.setChecked(s.url_font_follows_text)
        self.url_color_selector.set_from_color(s.url_color)
        self.color_links_check.setChecked(s.color_links)
        self.color_links_check.stateChanged.emit(self.color_links_check.isChecked())


class SettingsHeading(QLabel):
    pass


class LatexPaperSelector(QComboBox):
    _text_to_paper = {"A4": "a4paper", "Letter": "letterpaper"}
    _paper_to_text = {v: k for k, v in _text_to_paper.items()}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.addItems(sorted(self._text_to_paper))

    def get_paper(self):
        return self._text_to_paper[self.currentText()]

    def set_from_paper(self, paper: str):
        self.setCurrentText(self._paper_to_text[paper])


class LatexFontSizeSelector(QSpinBox):
    _commands = ["normalsize", "large", "Large", "LARGE", "huge", "Huge"]
    _value_to_command = dict(enumerate(_commands, start=1))
    _command_to_value = {v: k for k, v in _value_to_command.items()}

    def __init__(self, parent=None):
        super().__init__(parent, minimum=1, maximum=len(self._commands), prefix="Size ")

    def get_command(self):
        return self._value_to_command[super().value()]

    def set_from_command(self, command: str):
        self.setValue(self._command_to_value[command])


class LatexColorSelector(QComboBox):
    _texts = [
        s.title()
        for s in [
            "black",
            "blue",
            "brown",
            "cyan",
            "dark gray",
            "gray",
            "green",
            "light gray",
            "lime",
            "magenta",
            "olive",
            "orange",
            "pink",
            "purple",
            "red",
            "teal",
            "violet",
            "white",
            "yellow",
        ]
    ]
    _text_to_color = {k: k.lower().replace(" ", "") for k in _texts}
    _color_to_text = {v: k for k, v in _text_to_color.items()}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.addItems(sorted(self._texts))

    def get_color(self):
        return self._text_to_color[self.currentText()]

    def set_from_color(self, color: str):
        self.setCurrentText(self._color_to_text[color])


class DateFormatSelector(QComboBox):
    _sample_date = SmartDate(year=2022, month=11, day=1)
    _sample_to_style = {}
    for style in [
        "american",
        "american long",
        "american slash",
        "british",
        "british long",
        "british slash",
        "iso",
        "yyyy/mm/dd",
    ]:
        key = _sample_date.to_str(style=style)
        _sample_to_style[key] = style

    del style
    del key

    def __init__(self, parent=None):
        super().__init__(parent)
        self.addItems(sorted(self._sample_to_style))

    def get_style(self):
        return self._sample_to_style[self.currentText()]

    def set_from_style(self, style: str):
        self.setCurrentText(self._sample_date.to_str(style=style))


class Separator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)


def _ask_yesno(
    *,
    parent=None,
    text="",
    title=APP_TITLE,
    icon=QMessageBox.Icon.Question,
    default_yes=True,
):
    msg_box = QMessageBox(parent=parent, text=text, icon=icon)
    msg_box.setWindowTitle(title)
    _ = QMessageBox.StandardButton
    msg_box.setStandardButtons(_.Yes | _.No)
    msg_box.setDefaultButton(_.Yes if default_yes else _.No)
    return msg_box.exec() == _.Yes


def _show_error(*, parent=None, text="", title=APP_TITLE):
    msg_box = QMessageBox(parent=parent, text=text)
    msg_box.setWindowTitle(title)
    msg_box.setIcon(QMessageBox.Icon.Critical)
    return msg_box.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    test_settings = Settings()
    window.settings_frame.load_settings(test_settings)
    sys.exit(app.exec())
