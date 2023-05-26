import sys
import os
import traceback
import dataclasses
import json

from PyQt6.QtCore import Qt, QProcess
from PyQt6.QtGui import (
    QAction,
    QKeySequence,
    QFont,
    QColor,
    QPalette,
    QCloseEvent,
)
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QPlainTextEdit,
    QTextEdit,
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
import chat

APP_TITLE = "Curriculum Victim"
LAST_USED_SETTINGS = "settings/last_used.json"
LAST_USED_CONFIG = "config/last_used.json"


@dataclasses.dataclass
class Config:
    # editor
    editor_font: str = "Consolas"
    editor_font_size: int = 12
    editor_foreground: str = "#000000"
    editor_background: str = "#ffffff"
    editor_wrap_lines: bool = True

    # console
    console_font: str = "Consolas"
    console_font_size: int = 10
    console_foreground: str = "#205e80"
    console_background: str = "#f7f7f7"
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
        self._windows = []  # stand-alone prompt windows
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

        # create actions
        # File and app actions
        self._a_new = QAction("&New", self)
        self._a_new.triggered.connect(self.new_file)
        self._a_new.setShortcut(QKeySequence("Ctrl+n"))

        self._a_newblank = QAction("New &Blank", self)
        self._a_newblank.triggered.connect(self.new_blank_file)
        self._a_newblank.setShortcut(QKeySequence("Ctrl+Shift+n"))

        self._a_open = QAction("&Open...", self)
        self._a_open.triggered.connect(self.open_file)
        self._a_open.setShortcut(QKeySequence("Ctrl+o"))

        self._a_reload = QAction("&Reload", self)
        self._a_reload.triggered.connect(self.reload_file)
        self._a_reload.setShortcut(QKeySequence("F5"))
        self._a_reload.setDisabled(True)

        self._a_save = QAction("&Save", self)
        self._a_save.triggered.connect(self.save_file)
        self._a_save.setShortcut(QKeySequence("Ctrl+s"))

        self._a_saveas = QAction("Save &As...", self)
        self._a_saveas.triggered.connect(self.save_file_as)
        self._a_saveas.setShortcut(QKeySequence("Ctrl+Shift+s"))

        self._a_quit = QAction("&Quit", self)
        self._a_quit.triggered.connect(self.close)
        self._a_quit.setShortcut(QKeySequence("Ctrl+q"))

        # Edit actions
        self._a_undo = QAction("&Undo", self)
        self._a_undo.triggered.connect(self.editor.undo)
        self._a_undo.setShortcut("Ctrl+z")

        self._a_redo = QAction("&Redo", self)
        self._a_redo.triggered.connect(self.editor.redo)
        self._a_redo.setShortcut("Ctrl+y")

        self._a_cut = QAction("Cu&t", self)
        self._a_cut.triggered.connect(self.editor.cut)
        self._a_cut.setShortcut("Ctrl+x")

        self._a_copy = QAction("&Copy", self)
        self._a_copy.triggered.connect(self.editor.copy)
        self._a_copy.setShortcut("Ctrl+c")

        self._a_paste = QAction("&Paste", self)
        self._a_paste.triggered.connect(self.editor.paste)
        self._a_paste.setShortcut("Ctrl+v")

        self._a_selectall = QAction("Select &All", self)
        self._a_selectall.triggered.connect(self.editor.selectAll)
        self._a_selectall.setShortcut(QKeySequence("Ctrl+a"))

        # TODO
        # self._a_goto = QAction("&Go to Line...", self)
        # self._a_goto.triggered.connect(lambda: print("editor.goto_line"))
        # self._a_goto.setShortcut(QKeySequence("Ctrl+g"))
        # self._a_goto.setDisabled(True)

        # TODO
        self._a_find = QAction("&Find...", self)
        self._a_find.triggered.connect(lambda: print("editor.find"))
        self._a_find.setShortcut(QKeySequence("Ctrl+f"))
        self._a_find.setDisabled(True)

        # TODO
        self._a_replace = QAction("&Replace...", self)
        self._a_replace.triggered.connect(lambda: print("editor.replace"))
        self._a_replace.setShortcut(QKeySequence("Ctrl+h"))
        self._a_replace.setDisabled(True)

        self._a_insertact = QAction("&Activity", self)
        self._a_insertact.triggered.connect(self.insert_activity)
        self._a_insertact.setShortcut(QKeySequence("Ctrl+Alt+a"))

        self._a_insertaward = QAction("Awar&d", self)
        self._a_insertaward.triggered.connect(self.insert_award)
        self._a_insertaward.setShortcut(QKeySequence("Ctrl+Alt+d"))

        self._a_insertedu = QAction("&Education", self)
        self._a_insertedu.triggered.connect(self.insert_education)
        self._a_insertedu.setShortcut(QKeySequence("Ctrl+Alt+e"))

        self._a_insertskills = QAction("&Skillset", self)
        self._a_insertskills.triggered.connect(self.insert_skillset)
        self._a_insertskills.setShortcut(QKeySequence("Ctrl+Alt+s"))

        self._a_inserttest = QAction("&Test", self)
        self._a_inserttest.triggered.connect(self.insert_test)
        self._a_inserttest.setShortcut(QKeySequence("Ctrl+Alt+t"))

        # LaTeX actions
        self._a_parse = QAction("&Parse", self)
        self._a_parse.triggered.connect(self.show_parse_tree)
        self._a_parse.setShortcut(QKeySequence("Ctrl+`"))
        self._a_parse.setToolTip("Show the parse tree in the log window")

        self._a_runlatex = QAction("&Run", self)
        self._a_runlatex.triggered.connect(self.run_latex)
        self._a_runlatex.setShortcut(QKeySequence("Ctrl+Shift+r"))

        self._a_importsettings = QAction("&Import Settings...", self)
        self._a_importsettings.triggered.connect(self.import_settings)
        self._a_importsettings.setShortcut(QKeySequence("Ctrl+i"))
        self._a_importsettings.setToolTip("Load LaTeX settings from a file")

        self._a_exportsettings = QAction("&Export Settings...", self)
        self._a_exportsettings.triggered.connect(self.export_settings)
        self._a_exportsettings.setShortcut(QKeySequence("Ctrl+e"))
        self._a_exportsettings.setToolTip("Save current LaTeX settings to a file")

        self._a_restoredefault = QAction("Restore &Default", self)
        self._a_restoredefault.triggered.connect(self.restore_default)
        self._a_restoredefault.setShortcut(QKeySequence("Ctrl+Shift+d"))
        self._a_restoredefault.setToolTip("Restore default LaTeX settings")

        # Editor options
        self._a_largerfont = QAction("Zoom &In", self)
        self._a_largerfont.triggered.connect(self.increment_editor_font_size)
        self._a_largerfont.setShortcut(QKeySequence("Ctrl+="))

        self._a_smallerfont = QAction("Zoom &Out", self)
        self._a_smallerfont.triggered.connect(self.decrement_editor_font_size)
        self._a_smallerfont.setShortcut(QKeySequence("Ctrl+-"))

        self._a_togglewrap = QAction("&Wrap Lines", self)
        self._a_togglewrap.triggered.connect(self.toggle_wrap)
        self._a_togglewrap.setShortcut(QKeySequence("Alt+z"))
        self._a_togglewrap.setCheckable(True)

        self._a_configdialog = QAction("&More...", self)
        self._a_configdialog.triggered.connect(self.open_config_window)
        self._a_configdialog.setShortcut(QKeySequence("Ctrl+,"))

        self._a_enterprompt = QAction("&Enter Prompt...", self)
        self._a_enterprompt.triggered.connect(self.open_prompt_window)
        self._a_enterprompt.setShortcut(QKeySequence("Ctrl+Shift+e"))

        self._gpt_actions = self._create_gpt_actions()

        self._create_menus()
        self._update_ui_with_config()

        self.editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self.show_context_menu)

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

    def _create_menus(self):
        # File menu
        file_menu = QMenu("&File", self)
        file_menu.setToolTipsVisible(True)
        self.menubar.addMenu(file_menu)

        file_menu.addAction(self._a_new)
        file_menu.addAction(self._a_newblank)
        file_menu.addSeparator()
        file_menu.addAction(self._a_open)
        file_menu.addAction(self._a_reload)
        file_menu.addSeparator()
        file_menu.addAction(self._a_save)
        file_menu.addAction(self._a_saveas)
        file_menu.addSeparator()
        file_menu.addAction(self._a_quit)

        # Edit menu
        edit_menu = QMenu("&Edit", self)
        edit_menu.setToolTipsVisible(True)
        self.menubar.addMenu(edit_menu)

        edit_menu.addAction(self._a_undo)
        edit_menu.addAction(self._a_redo)
        edit_menu.addSeparator()
        edit_menu.addAction(self._a_cut)
        edit_menu.addAction(self._a_copy)
        edit_menu.addAction(self._a_paste)
        edit_menu.addSeparator()
        edit_menu.addAction(self._a_selectall)
        # edit_menu.addAction(self._a_goto)
        edit_menu.addAction(self._a_find)
        edit_menu.addAction(self._a_replace)
        edit_menu.addSeparator()

        insertion_menu = QMenu("&Insert", self)
        edit_menu.addMenu(insertion_menu)
        insertion_menu.addAction(self._a_insertact)
        insertion_menu.addAction(self._a_insertaward)
        insertion_menu.addAction(self._a_insertedu)
        insertion_menu.addAction(self._a_insertskills)
        insertion_menu.addAction(self._a_inserttest)

        # ChatGPT menu
        self._gpt_menu = self._create_gpt_menu()
        self.menubar.addMenu(self._gpt_menu)

        # LaTeX menu
        latex_menu = QMenu("La&TeX", self)
        latex_menu.setToolTipsVisible(True)
        self.menubar.addMenu(latex_menu)

        latex_menu.addAction(self._a_parse)
        latex_menu.addAction(self._a_runlatex)
        latex_menu.addSeparator()
        latex_menu.addAction(self._a_importsettings)
        latex_menu.addAction(self._a_exportsettings)
        latex_menu.addAction(self._a_restoredefault)

        # Options menu
        options_menu = QMenu("&Options", self)
        options_menu.setToolTipsVisible(True)
        self.menubar.addMenu(options_menu)

        options_menu.addAction(self._a_largerfont)
        options_menu.addAction(self._a_smallerfont)
        options_menu.addSeparator()
        options_menu.addAction(self._a_togglewrap)
        options_menu.addSeparator()
        options_menu.addAction(self._a_configdialog)

    def show_context_menu(self, position):
        context_menu = self.editor.createStandardContextMenu()
        context_menu.addSeparator()

        # insertion actions
        context_insertion_menu = QMenu("Insert", self)
        context_menu.addMenu(context_insertion_menu)
        context_insertion_menu.addAction(self._a_insertact)
        context_insertion_menu.addAction(self._a_insertedu)
        context_insertion_menu.addAction(self._a_insertskills)
        context_insertion_menu.addAction(self._a_inserttest)
        context_insertion_menu.addAction(self._a_insertaward)
        # gpt menu and actions
        context_menu.addMenu(self._gpt_menu)

        context_menu.exec(self.editor.mapToGlobal(position))

    def _create_gpt_actions(self) -> list[QAction]:
        actions = []
        try:
            prompt_filenames = sorted(os.listdir("prompts"))
        except FileNotFoundError:
            prompt_filenames = []

        for filename in prompt_filenames:
            action_name, _ = os.path.splitext(filename)
            action = QAction(action_name, self)
            with open(f"prompts/{filename}", encoding="utf-8") as f:
                prompt_head = f.read().strip()

            def _slot(*_, prompt_head=prompt_head):
                self._exec_prompt(prompt_head)

            action.triggered.connect(_slot)
            actions.append(action)

        actions.append(self._a_enterprompt)
        return actions

    def _create_gpt_menu(self) -> QMenu:
        menu = QMenu("Chat&GPT", self)
        for i, action in enumerate(self._gpt_actions):
            # separate user-defined actions from built-in ones
            if i and action is self._a_enterprompt:
                menu.addSeparator()
            menu.addAction(action)
        if not chat.openai.api_key:
            menu.setDisabled(True)
        return menu

    def _exec_prompt(self, prompt_head: str):
        gpt = chat.Chat(model="gpt-3.5-turbo")
        prompt_tail = self.editor.get_selected()
        prompt = f"{prompt_head}\n\n{prompt_tail}".strip()
        try:
            self.console.clear()
            self.console.append(f"<b>>>> Prompt</b>")
            self.console.append(prompt)
            self.console.append("<b>>>></b>")
            QApplication.processEvents()

            self.console.append(f"<b>>>> {gpt.model}</b>")
            self.console.append("")
            for content, _ in gpt.get_chunks(prompt, assistant=False):
                self.console.insertPlainText(content)
                self.console.ensureCursorVisible()
                QApplication.processEvents()  # force update
            self.console.append("<b>>>></b>")

        except Exception as e:
            self._handle_exc(e)

    def _update_ui_with_config(self):
        # editor font and line wrap
        editor_font = QFont(self._config.editor_font, self._config.editor_font_size)
        self.editor.setFont(editor_font)
        if self._config.editor_wrap_lines:
            self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # editor foreground & background
        editor_palette = self.editor.palette()
        editor_palette.setColor(
            QPalette.ColorGroup.Normal,
            QPalette.ColorRole.Base,
            QColor(self._config.editor_background),
        )
        editor_palette.setColor(
            QPalette.ColorGroup.Normal,
            QPalette.ColorRole.Text,
            QColor(self._config.editor_foreground),
        )
        self.editor.setPalette(editor_palette)

        # console font and line wrap
        console_font = QFont(self._config.console_font, self._config.console_font_size)
        self.console.setFont(console_font)
        if self._config.console_wrap_lines:
            self.console.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.console.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

        # console foreground & background
        console_palette = self.console.palette()
        console_palette.setColor(
            QPalette.ColorGroup.Normal,
            QPalette.ColorRole.Base,
            QColor(self._config.console_background),
        )
        console_palette.setColor(
            QPalette.ColorGroup.Normal,
            QPalette.ColorRole.Text,
            QColor(self._config.console_foreground),
        )
        self.console.setPalette(console_palette)

        # menu items
        self._a_togglewrap.setChecked(self._config.editor_wrap_lines)

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
            for w in self._windows:
                w.close()
            event.accept()

    def show_parse_tree(self):
        try:
            cv, unparsed = txtparse.parse(self.editor.toPlainText())
            self.console.setPlainText(cv.to_json())
        except Exception as e:
            self._handle_exc(e)
            return
        if unparsed:
            lines = "\n".join(map(repr, unparsed))
            show_info(parent=self, text=f"Unable to parse lines:\n\n{lines}")

    def run_latex(self):
        self.run_button.setDisabled(True)
        self._a_runlatex.setDisabled(True)
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
        self.console.append(output)

    def _handle_proc_finish(self, exit_code, exit_status):
        # re-enable UI
        self.run_button.setDisabled(False)
        self._a_runlatex.setDisabled(False)
        # clean up
        silent_remove("output.aux")
        silent_remove("output.log")
        silent_remove("output.out")
        silent_remove("output.synctex(busy)")
        silent_remove("output.synctex.gz")

        # handle errors if any
        if exit_code != 0 or exit_status != QProcess.ExitStatus.NormalExit:
            message = f"{exit_code=}, {exit_status=}"
            show_error(parent=self, text=f"Sorry, something went wrong.\n\n{message}")
            return

        self.console.append("Operation completed successfully.")
        try:
            if self._config.open_pdf_when_done:
                os.startfile("output.pdf")
        except Exception as e:
            self._handle_exc(e)

    def _handle_exc(self, e: Exception):
        self.console.append(traceback.format_exc())
        show_error(parent=self, text=f"{e.__class__.__name__}\n\n{e}")

    def _update_filepath(self):
        if self._filepath:
            filename = os.path.basename(self._filepath)
            self._a_reload.setDisabled(False)
            self._a_reload.setText(f"Reload {filename}")
        else:
            filename = "untitled"
            self._a_reload.setDisabled(True)
            self._a_reload.setText("Reload")
        self.setWindowTitle(f"{filename}[*] - {APP_TITLE}")
        self.setWindowFilePath(self._filepath)

    def _on_editor_change(self):
        self.setWindowModified(self.document.isModified())

    def new_file(self):
        self.editor.setPlainText(txtparse.MODEL_CV)
        self._filepath = ""
        self._update_filepath()
        self.setWindowModified(False)
        self.console.clear()

    def new_blank_file(self):
        self.editor.setPlainText("")
        self._filepath = ""
        self._update_filepath()
        self.setWindowModified(False)
        self.console.clear()

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

    def open_file(self):
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
            try:
                self._config = w.get_config()
                self._update_ui_with_config()
            except Exception as e:
                self._handle_exc(e)
            finally:
                w.close()

        w.ok_button.clicked.connect(_get_config)
        w.exec()

    def open_prompt_window(self):
        w = PromptWindow()
        w.setWindowTitle("Enter Your Prompt")

        def _run():
            prompt_head = w.get_prompt()
            self._exec_prompt(prompt_head)

        w.send.triggered.connect(_run)
        self._windows.append(w)
        w.show()


class PromptWindow(QDialog):
    def __init__(self):
        super().__init__(None, Qt.WindowType.Window)
        self.send = QAction(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.editor = QPlainTextEdit(self)
        self.editor.setFrameShape(QFrame.Shape.NoFrame)
        self.document = self.editor.document()
        self.document.setDocumentMargin(6)
        layout.addWidget(self.editor)

        send_button = QPushButton("Send", self)
        send_button.clicked.connect(self.send.trigger)
        send_button.setToolTip("Alternatively, press Ctrl+Return")
        layout.addWidget(send_button)

        # trigger self.run_action with ctrl+return
        self.addAction(self.send)
        self.send.setShortcut(QKeySequence("Ctrl+Return"))

    def get_prompt(self):
        return self.editor.toPlainText()

    def set_prompt(self, prompt):
        self.editor.setPlainText(prompt)


class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        self.setLayout(layout)
        space_after_group = 20
        space_within_group = 5

        layout.addWidget(QLabel("Editor Font"))
        self.editor_font_selector = QFontComboBox(self)
        layout.addWidget(self.editor_font_selector)
        self.editor_font_size_selector = QSpinBox(self, minimum=8, suffix=" pt")
        layout.addWidget(self.editor_font_size_selector)
        layout.addSpacing(space_within_group)

        self.editor_wrap_check = QCheckBox("Wrap lines", self)
        layout.addWidget(self.editor_wrap_check)

        layout.addSpacing(space_after_group)

        layout.addWidget(QLabel("Log Window Font"))
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
        layout.addWidget(QLabel("Text Font"))
        self.text_font_selector = QFontComboBox(self)
        layout.addWidget(self.text_font_selector)
        self.text_size_selector = QSpinBox(self, minimum=8, maximum=14, suffix=" pt")
        layout.addWidget(self.text_size_selector)
        layout.addSpacing(space_after_group)

        # heading font
        layout.addWidget(QLabel("Heading Font"))
        self.heading_font_selector = QFontComboBox(self)
        layout.addWidget(self.heading_font_selector)
        self.heading_size_selector = LatexFontSizeSelector(self)
        layout.addWidget(self.heading_size_selector)
        layout.addSpacing(space_after_group)

        # title font
        layout.addWidget(QLabel("Title Font"))
        self.title_font_selector = QFontComboBox(self)
        layout.addWidget(self.title_font_selector)
        self.title_size_selector = LatexFontSizeSelector(self)
        layout.addWidget(self.title_size_selector)
        layout.addSpacing(space_after_group)

        # font features
        layout.addWidget(QLabel("Number Style"))
        self.proportional_numbers_check = QCheckBox("Proportional", self)
        layout.addWidget(self.proportional_numbers_check)
        self.oldstyle_numbers_check = QCheckBox("Old Style", self)
        layout.addWidget(self.oldstyle_numbers_check)
        layout.addSpacing(space_after_group)

        layout.addWidget(Separator(self))
        layout.addSpacing(space_after_separator)

        # paper
        layout.addWidget(QLabel("Paper"))
        self.paper_selector = LatexPaperSelector(self)
        layout.addWidget(self.paper_selector)
        layout.addSpacing(space_after_group)

        # margins
        layout.addWidget(QLabel("Margins"))
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

        layout.addWidget(QLabel("Line Height"))
        self.line_spread_selector = QDoubleSpinBox(self)
        self.line_spread_selector.setSingleStep(0.1)
        layout.addWidget(self.line_spread_selector)
        layout.addSpacing(space_within_group)

        layout.addWidget(QLabel("Space Between Paragraphs"))
        self.paragraph_skip_selector = QSpinBox(self, suffix=" pt")
        layout.addWidget(self.paragraph_skip_selector)
        layout.addSpacing(space_within_group)

        layout.addWidget(QLabel("Space Between Entries"))
        self.entry_skip_selector = QSpinBox(self, suffix=" pt")
        layout.addWidget(self.entry_skip_selector)
        layout.addSpacing(space_within_group)

        layout.addWidget(QLabel("Space Before Section Titles"))
        self.before_sectitle_skip_selector = QSpinBox(self, suffix=" pt")
        layout.addWidget(self.before_sectitle_skip_selector)
        layout.addSpacing(space_within_group)

        layout.addWidget(QLabel("Space After Section Titles"))
        self.after_sectitle_skip_selector = QSpinBox(self, suffix=" pt")
        layout.addWidget(self.after_sectitle_skip_selector)
        layout.addSpacing(space_after_group)

        layout.addWidget(Separator(self))
        layout.addSpacing(space_after_separator)

        # headings
        layout.addWidget(QLabel("Section Title Style"))
        self.bold_headings_check = QCheckBox("Bold", self)
        layout.addWidget(self.bold_headings_check)
        self.all_cap_headings_check = QCheckBox("All Caps", self)
        layout.addWidget(self.all_cap_headings_check)
        layout.addSpacing(space_after_group)

        # activities section title
        layout.addWidget(QLabel("Default Activities Section Title"))
        self.default_activities_title_edit = QLineEdit(self)
        layout.addWidget(self.default_activities_title_edit)
        layout.addSpacing(space_within_group)

        # awards section title
        layout.addWidget(QLabel("Awards Section Title"))
        self.awards_title_edit = QLineEdit(self)
        layout.addWidget(self.awards_title_edit)
        layout.addSpacing(space_within_group)

        # skills section title
        layout.addWidget(QLabel("Skills Section Title"))
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
        layout.addWidget(QLabel("Contact Divider"))
        self.contact_divider_edit = QLineEdit(self)
        layout.addWidget(self.contact_divider_edit)
        layout.addSpacing(space_after_group)

        # bullet appearance
        layout.addWidget(QLabel("Bullet Text"))
        self.bullet_text_edit = QLineEdit(self)
        layout.addWidget(self.bullet_text_edit)
        layout.addSpacing(space_within_group)

        layout.addWidget(QLabel("Bullet Indent"))
        self.bullet_indent_selector = QDoubleSpinBox(self, suffix=" em")
        self.bullet_indent_selector.setSingleStep(0.1)
        self.bullet_indent_selector.setDecimals(1)
        layout.addWidget(self.bullet_indent_selector)
        layout.addSpacing(space_within_group)

        layout.addWidget(QLabel("Bullet-Item Separation"))
        self.bullet_item_sep_selector = QDoubleSpinBox(self, suffix=" em")
        self.bullet_item_sep_selector.setSingleStep(0.1)
        self.bullet_item_sep_selector.setDecimals(1)
        layout.addWidget(self.bullet_item_sep_selector)
        layout.addSpacing(space_within_group)

        layout.addWidget(QLabel("Handle ending periods"))
        self.period_policy_selector = PeriodPolicySelector(self)
        layout.addWidget(self.period_policy_selector)
        layout.addSpacing(space_after_group)

        layout.addWidget(Separator(self))
        layout.addSpacing(space_after_separator)

        # date format
        layout.addWidget(QLabel("Date Format"))
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

        layout.addWidget(QLabel("URL Color"))
        self.url_color_selector = LatexColorSelector(self)
        layout.addWidget(self.url_color_selector)
        layout.addSpacing(space_after_group)

        # handle event
        self.color_links_check.stateChanged.connect(self._update_urlcolor_selector)

    def _update_urlcolor_selector(self):
        selectable = self.color_links_check.isChecked()
        self.url_color_selector.setEnabled(selectable)

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

        s.bold_award_names = self.bold_award_names_check.isChecked()
        s.bold_skillset_names = self.bold_skillset_names_check.isChecked()

        s.contact_divider = self.contact_divider_edit.text()

        s.bullet_text = self.bullet_text_edit.text()
        s.bullet_indent_in_em = self.bullet_indent_selector.value()
        s.bullet_item_sep_in_em = self.bullet_item_sep_selector.value()

        s.ending_period_policy = self.period_policy_selector.get_policy()

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

        self.bold_award_names_check.setChecked(s.bold_award_names)
        self.bold_skillset_names_check.setChecked(s.bold_skillset_names)

        self.contact_divider_edit.setText(s.contact_divider)

        self.bullet_text_edit.setText(s.bullet_text)
        self.bullet_indent_selector.setValue(s.bullet_indent_in_em)
        self.bullet_item_sep_selector.setValue(s.bullet_item_sep_in_em)

        self.period_policy_selector.set_from_policy(s.ending_period_policy)

        self.date_style_selector.set_from_style(s.date_style)
        self.url_follows_text_check.setChecked(s.url_font_follows_text)
        self.url_color_selector.set_from_color(s.url_color)
        self.color_links_check.setChecked(s.color_links)
        self.color_links_check.stateChanged.emit(self.color_links_check.isChecked())


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


class PeriodPolicySelector(QComboBox):
    _policies_to_texts = {
        "": "Do nothing",
        "add": "Add periods if missing",
        "remove": "Remove periods if present",
    }

    _texts_to_policies = {v: k for k, v in _policies_to_texts.items()}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.addItems(list(self._texts_to_policies))

    def get_policy(self):
        return self._texts_to_policies[self.currentText()]

    def set_from_policy(self, policy: str):
        self.setCurrentText(self._policies_to_texts[policy])


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
        key = tex.format_date(_sample_date, style=style)
        _sample_to_style[key] = style

    del style
    del key

    def __init__(self, parent=None):
        super().__init__(parent)
        self.addItems(sorted(self._sample_to_style))

    def get_style(self):
        return self._sample_to_style[self.currentText()]

    def set_from_style(self, style: str):
        self.setCurrentText(tex.format_date(self._sample_date, style))


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

    def get_selected(self):
        return self.textCursor().selectedText()


class Console(QTextEdit):
    # handles process outputs and supports auto-scrolling

    def append(self, text: str):
        super().append(text)
        self.ensureCursorVisible()


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


def silent_remove(filepath):
    try:
        os.remove(filepath)
    except OSError:
        pass


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
