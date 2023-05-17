import sys
import os
import traceback
import dataclasses
import json

from PyQt6.QtCore import Qt, QRegularExpression, QProcess
from PyQt6.QtGui import (
    QAction,
    QKeySequence,
    QFont,
    QCloseEvent,
    QRegularExpressionValidator,
)
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QPlainTextEdit,
    QFrame,
    QDialog,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QHBoxLayout,
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

import txtparse
import tex

APP_TITLE = "Curriculum Victim"
LAST_USED_SETTINGS = "settings/last_used.json"
LAST_USED_CONFIG = "config/last_used.json"

# For validating input
SAFE_LATEX = QRegularExpression(r"[^\\~#$%^&_{}]*")


@dataclasses.dataclass
class Config:
    # editor
    editor_font: str = "Consolas"
    editor_font_size: int = 12
    editor_wrap_lines: bool = True

    # console
    console_font: str = "Consolas"
    console_font_size: int = 10
    console_wrap_lines: bool = True

    # file system
    default_open_dir: str = ""
    default_save_dir: str = ""
    default_output_dir: str = ""
    open_pdf_when_done: bool = True

    @classmethod
    def from_json(cls, filepath: str) -> "Config":
        with open(filepath, encoding="utf-8") as f:
            return cls(**json.load(f))

    def to_json(self, filepath: str, indent=4):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(dataclasses.asdict(self), f, indent=indent)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._filepath = ""
        self._config = self._get_config()
        self.menubar = self.menuBar()

        # Main widget
        central_widget = QSplitter(self)
        self.setCentralWidget(central_widget)

        # Left panel
        editor_panel = QSplitter(Qt.Orientation.Vertical, self)
        central_widget.addWidget(editor_panel)

        # Editor
        self.editor = CvEditor(self)
        self.editor.setFrameShape(QFrame.Shape.NoFrame)
        self.document = self.editor.document()
        self.document.setDocumentMargin(6)
        self.editor.textChanged.connect(self._on_editor_change)
        editor_panel.addWidget(self.editor)

        # Console
        self.console = Console(self)
        self.console.setFrameShape(QFrame.Shape.NoFrame)
        self.console.setReadOnly(True)
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

        button_frame = QFrame(self)
        control_panel_layout.addWidget(button_frame)
        button_frame_layout = QGridLayout()
        button_frame.setLayout(button_frame_layout)

        parse_button = QPushButton("Parse", self)
        parse_button.clicked.connect(self.show_parse_tree)
        parse_button.setToolTip("Show the parse tree in the log window")
        button_frame_layout.addWidget(parse_button, 0, 0)
        self.run_button = QPushButton("Run LaTeX", self)
        self.run_button.clicked.connect(self.run_latex)
        button_frame_layout.addWidget(self.run_button, 0, 1)

        # Populate menus; update UI
        self._create_menu()
        self._update_ui_with_config()

        # Set window properties
        self.setGeometry(200, 100, 1000, 660)
        central_widget.setSizes([680, 320])
        editor_panel.setSizes([450, 150])

        self.new_file()
        self._load_initial_settings()

    def _get_config(self):
        try:
            config = Config.from_json(LAST_USED_CONFIG)
        except FileNotFoundError:
            config = Config()
        return config

    def _create_menu(self):
        # File menu
        file_menu = QMenu("&File", self)
        file_menu.setToolTipsVisible(True)
        self.menubar.addMenu(file_menu)

        new_action = QAction("&New", self)
        new_action.triggered.connect(self.new_file)
        new_action.setShortcut(QKeySequence("Ctrl+n"))
        file_menu.addAction(new_action)

        new_blank_action = QAction("New &Blank", self)
        new_blank_action.triggered.connect(self.new_blank_file)
        new_blank_action.setShortcut(QKeySequence("Ctrl+Shift+n"))
        file_menu.addAction(new_blank_action)

        file_menu.addSeparator()

        open_action = QAction("&Open...", self)
        open_action.triggered.connect(self.open_file)
        open_action.setShortcut(QKeySequence("Ctrl+o"))
        file_menu.addAction(open_action)

        reload_action = QAction("&Reload", self)
        reload_action.triggered.connect(self.reload_file)
        reload_action.setShortcut(QKeySequence("F5"))
        reload_action.setToolTip("Reload the current file from disk")
        file_menu.addAction(reload_action)

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

        # Edit menu
        edit_menu = QMenu("&Edit", self)
        edit_menu.setToolTipsVisible(True)
        self.menubar.addMenu(edit_menu)

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

        select_all_action = QAction("Select &All", self)
        select_all_action.triggered.connect(self.editor.selectAll)
        select_all_action.setShortcut(QKeySequence("Ctrl+a"))
        edit_menu.addAction(select_all_action)

        goto_action = QAction("&Go to Line...", self)
        # TODO
        goto_action.triggered.connect(lambda: print("editor.goto_line"))
        goto_action.setDisabled(True)
        goto_action.setShortcut(QKeySequence("Ctrl+g"))
        edit_menu.addAction(goto_action)

        find_action = QAction("&Find...", self)
        # TODO
        find_action.triggered.connect(lambda: print("editor.find"))
        find_action.setDisabled(True)
        find_action.setShortcut(QKeySequence("Ctrl+f"))
        edit_menu.addAction(find_action)

        replace_action = QAction("&Replace...", self)
        # TODO
        replace_action.triggered.connect(lambda: print("editor.replace"))
        replace_action.setDisabled(True)
        replace_action.setShortcut(QKeySequence("Ctrl+h"))
        edit_menu.addAction(replace_action)

        edit_menu.addSeparator()

        insert_activity_action = QAction("Insert &Activity", self)
        insert_activity_action.triggered.connect(self.insert_activity)
        insert_activity_action.setShortcut(QKeySequence("Ctrl+Shift+a"))
        edit_menu.addAction(insert_activity_action)

        insert_edu_action = QAction("Insert &Education", self)
        insert_edu_action.triggered.connect(self.insert_education)
        insert_edu_action.setShortcut(QKeySequence("Ctrl+Shift+e"))
        edit_menu.addAction(insert_edu_action)

        insert_skillset_action = QAction("Insert S&killset", self)
        insert_skillset_action.triggered.connect(self.insert_skillset)
        insert_skillset_action.setShortcut(QKeySequence("Ctrl+Shift+k"))
        edit_menu.addAction(insert_skillset_action)

        insert_test_action = QAction("Insert &Test", self)
        insert_test_action.triggered.connect(self.insert_test)
        insert_test_action.setShortcut(QKeySequence("Ctrl+Shift+t"))
        edit_menu.addAction(insert_test_action)

        insert_award_action = QAction("Insert A&ward", self)
        insert_award_action.triggered.connect(self.insert_award)
        insert_award_action.setShortcut(QKeySequence("Ctrl+Shift+w"))
        edit_menu.addAction(insert_award_action)

        # LaTeX menu
        latex_menu = QMenu("La&TeX", self)
        latex_menu.setToolTipsVisible(True)
        self.menubar.addMenu(latex_menu)

        parse_action = QAction("&Parse", self)
        parse_action.triggered.connect(self.show_parse_tree)
        parse_action.setShortcut(QKeySequence("Ctrl+`"))
        parse_action.setToolTip("Show the parse tree in the log window")
        latex_menu.addAction(parse_action)

        self.run_latex_action = QAction("&Run LaTeX", self)
        self.run_latex_action.triggered.connect(self.run_latex)
        self.run_latex_action.setShortcut(QKeySequence("Ctrl+Shift+r"))
        latex_menu.addAction(self.run_latex_action)

        latex_menu.addSeparator()

        import_settings_action = QAction("&Import Settings...", self)
        import_settings_action.triggered.connect(self.import_settings)
        import_settings_action.setShortcut(QKeySequence("Ctrl+i"))
        import_settings_action.setToolTip("Load LaTeX settings from a file")
        latex_menu.addAction(import_settings_action)

        export_settings_action = QAction("&Export Settings...", self)
        export_settings_action.triggered.connect(self.export_settings)
        export_settings_action.setShortcut(QKeySequence("Ctrl+e"))
        export_settings_action.setToolTip("Save current LaTeX settings to a file")
        latex_menu.addAction(export_settings_action)

        restore_default_action = QAction("Restore &Default", self)
        restore_default_action.triggered.connect(self.restore_default)
        restore_default_action.setShortcut(QKeySequence("Ctrl+Shift+d"))
        latex_menu.addAction(restore_default_action)

        # Options menu
        options_menu = QMenu("&Options", self)
        options_menu.setToolTipsVisible(True)
        self.menubar.addMenu(options_menu)

        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.triggered.connect(self.increment_editor_font_size)
        zoom_in_action.setShortcut(QKeySequence("Ctrl+="))
        options_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.triggered.connect(self.decrement_editor_font_size)
        zoom_out_action.setShortcut(QKeySequence("Ctrl+-"))
        options_menu.addAction(zoom_out_action)

        options_menu.addSeparator()

        self.toggle_wrap_action = QAction("&Wrap Lines", self)
        self.toggle_wrap_action.triggered.connect(self.toggle_wrap)
        self.toggle_wrap_action.setShortcut(QKeySequence("Alt+z"))
        self.toggle_wrap_action.setCheckable(True)
        options_menu.addAction(self.toggle_wrap_action)

        options_menu.addSeparator()

        open_config_action = QAction("&More...", self)
        open_config_action.triggered.connect(self.open_config_window)
        open_config_action.setShortcut(QKeySequence("Ctrl+,"))
        options_menu.addAction(open_config_action)

    def _update_ui_with_config(self):
        # editor
        editor_font = QFont(self._config.editor_font, self._config.editor_font_size)
        self.editor.setFont(editor_font)
        if self._config.editor_wrap_lines:
            self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # console
        console_font = QFont(self._config.console_font, self._config.console_font_size)
        self.console.setFont(console_font)
        if self._config.console_wrap_lines:
            self.console.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.console.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # menu items
        self.toggle_wrap_action.setChecked(self._config.editor_wrap_lines)

    def _load_initial_settings(self):
        try:
            initial_settings = tex.Settings.from_json(LAST_USED_SETTINGS)
        except FileNotFoundError:
            initial_settings = tex.Settings()
        self.settings_frame.load_settings(initial_settings)

    def closeEvent(self, event: QCloseEvent):
        # Ask user to handle unsaved change if any
        if self.isWindowModified() and not _ask_yesno(
            parent=self,
            default_yes=True,
            text=(
                "Your document has unsaved changes.\n"
                "Discard the changes and close the program?"
            ),
        ):
            event.ignore()
        else:
            # Save current settings and config
            settings = self.settings_frame.get_settings()
            settings.to_json(LAST_USED_SETTINGS)
            self._config.to_json(LAST_USED_CONFIG)
            event.accept()

    def log(self, message: str):
        self.console.append(message)

    def show_parse_tree(self):
        try:
            cv, unparsed = txtparse.parse(self.editor.toPlainText())
            self.console.setPlainText(cv.to_json())
        except Exception as e:
            self._handle_exc(e)
            return
        if unparsed:
            lines = "\n".join(map(repr, unparsed))
            show_info(
                parent=self, text=f"Unable to parse the following lines:\n\n{lines}"
            )

    def run_latex(self):
        self.run_button.setDisabled(True)
        self.run_latex_action.setDisabled(True)
        self.console.clear()
        try:
            # TODO hard-coded paths
            template_path = "templates/classic.tex"
            tex_path = "output.tex"

            cv, _ = txtparse.parse(self.editor.toPlainText())
            settings = self.settings_frame.get_settings()
            rendered = tex.render(template_path=template_path, cv=cv, settings=settings)
            with open(tex_path, "w", encoding="utf-8") as tex_file:
                tex_file.write(rendered)

            proc = QProcess(self)
            proc.readyReadStandardOutput.connect(self._handle_proc_output)
            proc.finished.connect(self._handle_proc_finish)
            proc.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
            proc.start("lualatex", ["-interaction=nonstopmode", tex_path])

        except Exception as e:
            self._handle_exc(e)

    def _handle_proc_output(self):
        proc = self.sender()
        output = proc.readAllStandardOutput().data().decode()
        self.log(output)

    def _handle_proc_finish(self, exit_code, exit_status):
        # re-enable UI
        self.run_button.setDisabled(False)
        self.run_latex_action.setDisabled(False)

        # handle errors if any
        if exit_code != 0 or exit_status != QProcess.ExitStatus.NormalExit:
            show_error(
                parent=self,
                text=f"Sorry, something went wrong.\n" f"{exit_code=}, {exit_status=}",
            )
            return

        self.log("Operation completed successfully.")
        try:
            # clean up
            os.remove(f"output.aux")
            os.remove(f"output.log")
            os.remove(f"output.out")
            if self._config.open_pdf_when_done:
                os.startfile("output.pdf")
        except Exception as e:
            self._handle_exc(e)

    def _handle_exc(self, e: Exception):
        self.log(traceback.format_exc())
        show_error(parent=self, text=f"Oops, something went wrong.\n{e}")

    def _update_filepath(self):
        if self._filepath:
            filename = os.path.basename(self._filepath)
        else:
            filename = "untitled"
        self.setWindowTitle(f"{filename}[*] - {APP_TITLE}")
        self.setWindowFilePath(self._filepath)

    def _on_editor_change(self):
        self.setWindowModified(self.document.isModified())

    def new_file(self):
        self.editor.setPlainText(txtparse.MODEL_CV)
        self._filepath = ""
        self._update_filepath()
        self.setWindowModified(False)

    def new_blank_file(self):
        self.editor.setPlainText("")
        self._filepath = ""
        self._update_filepath()
        self.setWindowModified(False)

    def _open_file(self, filepath: str):
        try:
            with open(filepath, encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            self._handle_exc(e)
        else:
            self.editor.setPlainText(text)
            # set window title
            self.setWindowModified(False)
            self._filepath = filepath
            self._update_filepath()
            # show the parsed json in the console
            self.show_parse_tree()

    def open_file(self):
        # TODO last opened dir
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            caption="Open File",
            directory=self._config.default_open_dir,
            filter="TXT Files (*.txt)",
        )
        if filepath:
            # update config
            self._config.default_open_dir = os.path.dirname(filepath)
            self._open_file(filepath)

    def reload_file(self):
        self._open_file(self._filepath)

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
            self._handle_exc(e)

    def save_file_as(self):
        # TODO last saved dir
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            caption="Save File",
            directory=self._config.default_save_dir,
            filter="TXT Files (*.txt)",
        )
        if not filepath:
            return
        # update config, whether save successful or not
        self._config.default_save_dir = os.path.dirname(filepath)
        try:
            self._save_file(filepath=filepath)
        except Exception as e:
            self._handle_exc(e)
        else:
            self._filepath = filepath
            self._update_filepath()

    def insert_activity(self):
        self.editor.insert(txtparse.MODEL_ACTIVITY)

    def insert_education(self):
        self.editor.insert(txtparse.MODEL_EDUCATION)

    def insert_skillset(self):
        self.editor.insert(txtparse.MODEL_SKILLSET)

    def insert_test(self):
        self.editor.insert(txtparse.MODEL_TEST)

    def insert_award(self):
        self.editor.insert(txtparse.MODEL_AWARD)

    def import_settings(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            caption="Import Settings",
            directory="settings",
            filter="JSON Files (*.json)",
        )
        if not filepath:
            return
        settings = tex.Settings.from_json(filepath=filepath)
        self.settings_frame.load_settings(settings)

    def export_settings(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            caption="Export Settings",
            directory="settings",
            filter="JSON Files (*json)",
        )
        if not filepath:
            return
        settings = self.settings_frame.get_settings()
        settings.to_json(filepath=filepath)

    def restore_default(self):
        self.settings_frame.load_settings(tex.Settings())

    def increment_editor_font_size(self):
        self._config.editor_font_size += 1
        self._update_ui_with_config()

    def decrement_editor_font_size(self):
        if self._config.editor_font_size > 9:  # min size = 8
            self._config.editor_font_size -= 1
            self._update_ui_with_config()

    def toggle_wrap(self, state: bool):
        self._config.editor_wrap_lines = state
        self._config.console_wrap_lines = state
        self._update_ui_with_config()

    def open_config_window(self):
        w = ConfigDialog(self)
        w.setWindowTitle("Options")
        w.load_config(self._config)

        def _get_config():
            self._config = w.get_config()
            self._update_ui_with_config()
            w.close()

        w.ok_button.clicked.connect(_get_config)
        w.exec()


class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        self.setLayout(layout)
        space_after_group = 20
        space_within_group = 5

        layout.addWidget(SettingsHeading("Editor Font"))
        self.editor_font_selector = QFontComboBox(self)
        layout.addWidget(self.editor_font_selector)
        self.editor_font_size_selector = QSpinBox(self, minimum=8, suffix=" pt")
        layout.addWidget(self.editor_font_size_selector)
        layout.addSpacing(space_within_group)

        self.editor_wrap_check = QCheckBox("Wrap lines", self)
        layout.addWidget(self.editor_wrap_check)

        layout.addSpacing(space_after_group)

        layout.addWidget(SettingsHeading("Log Window Font"))
        self.console_font_selector = QFontComboBox(self)
        layout.addWidget(self.console_font_selector)
        self.console_font_size_selector = QSpinBox(self, minimum=8, suffix=" pt")
        layout.addWidget(self.console_font_size_selector)
        layout.addSpacing(space_within_group)

        self.console_wrap_check = QCheckBox("Wrap lines", self)
        layout.addWidget(self.console_wrap_check)

        layout.addSpacing(space_after_group)

        button_frame = QFrame(self)
        layout.addWidget(button_frame)
        button_frame_layout = QHBoxLayout()
        button_frame.setLayout(button_frame_layout)

        cancel_button = QPushButton("Cancel", self)
        cancel_button.clicked.connect(self.close)
        button_frame_layout.addWidget(cancel_button)

        self.ok_button = QPushButton("OK", self)
        button_frame_layout.addWidget(self.ok_button)

    def get_config(self) -> Config:
        c = Config()
        c.editor_font = self.editor_font_selector.currentFont().family()
        c.editor_font_size = self.editor_font_size_selector.value()
        c.editor_wrap_lines = self.editor_wrap_check.isChecked()
        c.console_font = self.console_font_selector.currentFont().family()
        c.console_font_size = self.console_font_size_selector.value()
        c.console_wrap_lines = self.console_wrap_check.isChecked()
        return c

    def load_config(self, config: Config):
        self.editor_font_selector.setCurrentFont(QFont(config.editor_font))
        self.editor_font_size_selector.setValue(config.editor_font_size)
        self.editor_wrap_check.setChecked(config.editor_wrap_lines)
        self.console_font_selector.setCurrentFont(QFont(config.console_font))
        self.console_font_size_selector.setValue(config.console_font_size)
        self.console_wrap_check.setChecked(config.console_wrap_lines)


class SettingsFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        self.setLayout(layout)
        space_after_group = 15
        space_within_group = 5
        space_after_separator = 10

        # ug/grad-specific settings
        self.activity_location_check = QCheckBox("Show Activity Locations", self)
        layout.addWidget(self.activity_location_check)
        self.time_commitment_check = QCheckBox("Show Time Commitments", self)
        layout.addWidget(self.time_commitment_check)
        layout.addSpacing(space_after_group)

        layout.addWidget(Separator(self))
        layout.addSpacing(space_after_separator)

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
        layout.addSpacing(space_within_group)

        layout.addWidget(SettingsHeading("Space Before Section Titles"))
        self.before_sectitle_skip_selector = QSpinBox(self, suffix=" pt")
        layout.addWidget(self.before_sectitle_skip_selector)
        layout.addSpacing(space_within_group)

        layout.addWidget(SettingsHeading("Space After Section Titles"))
        self.after_sectitle_skip_selector = QSpinBox(self, suffix=" pt")
        layout.addWidget(self.after_sectitle_skip_selector)
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

        self.bold_award_names_check = QCheckBox("Bold Award Names", self)
        layout.addWidget(self.bold_award_names_check)
        self.bold_skillset_names_check = QCheckBox("Bold Skillset Names", self)
        layout.addWidget(self.bold_skillset_names_check)
        layout.addSpacing(space_after_group)

        layout.addWidget(Separator(self))
        layout.addSpacing(space_after_separator)

        # contact divider
        layout.addWidget(SettingsHeading("Contact Divider"))
        self.contact_divider_edit = QLineEdit(self)
        validator = QRegularExpressionValidator(SAFE_LATEX, self.contact_divider_edit)
        self.contact_divider_edit.setValidator(validator)
        layout.addWidget(self.contact_divider_edit)
        layout.addSpacing(space_after_group)

        # bullet appearance
        layout.addWidget(SettingsHeading("Bullet Text"))
        self.bullet_text_edit = QLineEdit(self)
        validator = QRegularExpressionValidator(SAFE_LATEX, self.bullet_text_edit)
        self.bullet_text_edit.setValidator(validator)
        layout.addWidget(self.bullet_text_edit)
        layout.addSpacing(space_within_group)

        layout.addWidget(SettingsHeading("Bullet Indent"))
        self.bullet_indent_selector = QDoubleSpinBox(self, suffix=" em")
        self.bullet_indent_selector.setSingleStep(0.1)
        self.bullet_indent_selector.setDecimals(1)
        layout.addWidget(self.bullet_indent_selector)
        layout.addSpacing(space_within_group)

        layout.addWidget(SettingsHeading("Bullet-Item Separation"))
        self.bullet_item_sep_selector = QDoubleSpinBox(self, suffix=" em")
        self.bullet_item_sep_selector.setSingleStep(0.1)
        self.bullet_item_sep_selector.setDecimals(1)
        layout.addWidget(self.bullet_item_sep_selector)
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

    def get_settings(self) -> tex.Settings:
        s = tex.Settings()

        s.show_activity_locations = self.activity_location_check.isChecked()
        s.show_time_commitments = self.time_commitment_check.isChecked()

        s.main_font = self.text_font_selector.currentFont().family()
        s.font_size_in_point = self.text_size_selector.value()

        s.heading_font = self.heading_font_selector.currentFont().family()
        s.heading_relative_size = self.heading_size_selector.get_command()

        s.title_font = self.title_font_selector.currentFont().family()
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
        s.before_sectitle_skip_in_pt = self.before_sectitle_skip_selector.value()
        s.after_sectitle_skip_in_pt = self.after_sectitle_skip_selector.value()

        s.bold_headings = self.bold_headings_check.isChecked()
        s.all_cap_headings = self.all_cap_headings_check.isChecked()

        s.default_activities_section_title = self.default_activities_title_edit.text()
        s.awards_section_title = self.awards_title_edit.text()
        s.skills_section_title = self.skills_title_edit.text()

        s.contact_divider = self.contact_divider_edit.text()

        s.bullet_text = self.bullet_text_edit.text()
        s.bullet_indent_in_em = self.bullet_indent_selector.value()
        s.bullet_item_sep_in_em = self.bullet_item_sep_selector.value()

        s.bold_award_names = self.bold_award_names_check.isChecked()
        s.bold_skillset_names = self.bold_skillset_names_check.isChecked()

        s.date_style = self.date_style_selector.get_style()

        s.url_font_follows_text = self.url_follows_text_check.isChecked()
        s.color_links = self.color_links_check.isChecked()
        s.url_color = self.url_color_selector.get_color()

        return s

    def load_settings(self, s: tex.Settings):
        self.activity_location_check.setChecked(s.show_activity_locations)
        self.time_commitment_check.setChecked(s.show_time_commitments)

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
        self.before_sectitle_skip_selector.setValue(s.before_sectitle_skip_in_pt)
        self.after_sectitle_skip_selector.setValue(s.after_sectitle_skip_in_pt)

        self.bold_headings_check.setChecked(s.bold_headings)
        self.all_cap_headings_check.setChecked(s.all_cap_headings)

        self.default_activities_title_edit.setText(s.default_activities_section_title)
        self.awards_title_edit.setText(s.awards_section_title)
        self.skills_title_edit.setText(s.skills_section_title)

        self.contact_divider_edit.setText(s.contact_divider)

        self.bullet_text_edit.setText(s.bullet_text)
        self.bullet_indent_selector.setValue(s.bullet_indent_in_em)
        self.bullet_item_sep_selector.setValue(s.bullet_item_sep_in_em)

        self.bold_award_names_check.setChecked(s.bold_award_names)
        self.bold_skillset_names_check.setChecked(s.bold_skillset_names)

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
    _sample_date = txtparse.SmartDate(year=2022, month=11, day=1)
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


class CvEditor(QPlainTextEdit):
    # supports auto-scrolling

    def insert(self, text: str):
        self.insertPlainText(text)
        self.ensureCursorVisible()


class Console(QPlainTextEdit):
    # handles process outputs and supports auto-scrolling

    def append(self, text: str):
        self.appendPlainText(text)
        # scroll to bottom
        vbar = self.verticalScrollBar()
        vbar.setValue(vbar.maximum())


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


def show_message(*, parent=None, icon=None, **kwargs):
    msg_box = QMessageBox(parent=parent, **kwargs)
    msg_box.setWindowTitle(APP_TITLE)
    msg_box.setIcon(icon)
    return msg_box.exec()


def show_error(*, parent=None, text=""):
    return show_message(parent=parent, icon=QMessageBox.Icon.Critical, text=text)


def show_info(*, parent=None, text=""):
    return show_message(parent=parent, icon=QMessageBox.Icon.Information, text=text)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
