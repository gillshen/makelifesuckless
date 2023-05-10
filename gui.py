import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont
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
)

from render import Settings
from txtparse import FlexDate


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        menubar = self.menuBar()

        # File menu
        file_menu = QMenu("File", self)
        new_action = QAction("New", self)
        file_menu.addAction(new_action)
        open_action = QAction("Open", self)
        file_menu.addAction(open_action)
        save_action = QAction("Save", self)
        file_menu.addAction(save_action)
        save_as_action = QAction("Save as", self)
        file_menu.addAction(save_as_action)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        menubar.addMenu(file_menu)

        # Edit menu
        edit_menu = QMenu("Edit", self)
        undo_action = QAction("Undo", self)
        edit_menu.addAction(undo_action)
        redo_action = QAction("Redo", self)
        edit_menu.addAction(redo_action)
        copy_action = QAction("Copy", self)
        edit_menu.addAction(copy_action)
        paste_action = QAction("Paste", self)
        edit_menu.addAction(paste_action)
        menubar.addMenu(edit_menu)

        # View menu
        view_menu = QMenu("View", self)
        options_action = QAction("Show/Hide Options", self)
        view_menu.addAction(options_action)
        log_action = QAction("Show/Hide Console", self)
        view_menu.addAction(log_action)
        menubar.addMenu(view_menu)

        # Main widget
        central_widget = QSplitter(self)
        self.setCentralWidget(central_widget)

        # Left panel
        editor_panel = QSplitter(Qt.Orientation.Vertical, self)
        central_widget.addWidget(editor_panel)

        # Editor
        self.editor = QPlainTextEdit(self)
        self.editor.setFrameShape(QFrame.Shape.NoFrame)
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
        run_button.clicked.connect(lambda: print(self.get_settings()))
        control_panel_layout.addWidget(run_button)
        run_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        # Set window properties
        self.setGeometry(200, 100, 1000, 600)
        central_widget.setSizes([640, 360])
        editor_panel.setSizes([450, 150])
        self.setWindowTitle(" ")
        self.show()

    def get_settings(self) -> Settings:
        return self.settings_frame.get_settings()


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
    _sample_date = FlexDate(year=2022, month=11, day=1)
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    test_settings = Settings()
    window.settings_frame.load_settings(test_settings)
    sys.exit(app.exec())
