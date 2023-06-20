import os
import traceback
import dataclasses
import json
import time
import datetime
import csv

from PyQt6.QtCore import Qt, QProcess, QThread, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QFont,
    QColor,
    QCloseEvent,
    QFontMetrics,
    QTextCursor,
    QTextCharFormat,
)
from PyQt6.QtWidgets import (
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
    QSpacerItem,
)

import txtparse
import docparse
import tex
import chat
import excel
from cveditor import CvEditor

APP_TITLE = "Curriculum Victim"

SETTINGS_DIR = "settings"
LAST_USED_SETTINGS = f"{SETTINGS_DIR}/last_used.json"

CONFIG_DIR = "config"
LAST_USED_CONFIG = f"{CONFIG_DIR}/last_used.json"


@dataclasses.dataclass
class Config:
    # window geometry
    window_x: int = 200
    window_y: int = 100
    window_width: int = 1000
    window_height: int = 660

    # editor
    editor_font: str = "Consolas"
    editor_font_size: int = 10
    editor_foreground: str = "#000000"
    editor_background: str = "#ffffff"
    editor_wrap_lines: bool = True

    # syntax highlighting
    cv_default_foreground: str = "#000000"
    cv_keyword_foreground: str = "#1E90FF"  # dodger blue
    cv_keyword_bold: bool = True
    cv_bullet_foreground: str = "#DC143C"  # crimson
    cv_bullet_bold: bool = True
    cv_date_foreground: str = "#DA70D6"  # orchid
    cv_date_bold: bool = True
    cv_section_foreground: str = "#9400D3"  # dark orchid
    cv_section_bold: bool = True
    cv_unknown_foreground: str = "#FFA500"  # orange
    cv_unknown_bold: bool = False

    # console
    console_font: str = "Consolas"
    console_font_size: int = 10
    console_foreground: str = "#205E80"
    console_error_foreground: str = "#8B0000"  # dark red
    console_log_foreground: str = "#929fA5"
    console_background: str = "#F8F6F2"
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._menubar = self.menuBar()

        # editor and console appearance
        self._config = self._get_config()

        # chat completion parameters
        self._chat_params = chat.Params()
        self._params_window = ParamsDialog()
        self._decorate_params_dialog()

        # chat helpers
        self._gpt = chat.Chat()
        self._chat_threads = []
        self._excel_threads = []
        self._chat_history = None  # holds the path to the chat history file
        self._wait_count = 0

        # references to stand-alone GPT prompt windows
        self._prompt_window = GptWindow()
        self._prompt_window.setWindowTitle("Enter Your Prompt")
        self._prompt_window.resize(400, 320)
        self._prompt_window.send_action.triggered.connect(self._send_prompt)

        # path to the last opened file
        self._filepath = ""

        # Main widget
        central_widget = QSplitter(self)
        self.setCentralWidget(central_widget)

        # Left panel
        editor_panel = QSplitter(Qt.Orientation.Vertical, self)
        central_widget.addWidget(editor_panel)

        # Editor
        self.editor = CvEditor(self)
        self.editor.setObjectName("editor")
        self.editor.setFrameShape(QFrame.Shape.NoFrame)
        self.document = self.editor.document()
        self.document.setDocumentMargin(6)
        self.editor.textChanged.connect(self._on_editor_change)
        editor_panel.addWidget(self.editor)

        # Console
        self.console = Console(self)
        self.console.setObjectName("console")
        self.console.setFrameShape(QFrame.Shape.NoFrame)
        self.console.document().setDocumentMargin(6)
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

        self.settings_frame = LatexSettingsFrame(self)
        settings_area.setWidget(self.settings_frame)
        settings_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        settings_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        settings_area.setWidgetResizable(True)

        control_panel_layout.addSpacing(10)

        button_frame = QFrame(self)
        control_panel_layout.addWidget(button_frame)
        button_frame_layout = QHBoxLayout()
        button_frame.setLayout(button_frame_layout)

        self.run_button = QPushButton("Run LaTeX", self)
        self.run_button.clicked.connect(self.run_latex)
        self.run_button.setMinimumWidth(120)
        button_frame_layout.addWidget(
            self.run_button, alignment=Qt.AlignmentFlag.AlignRight
        )

        # create actions
        # File and app actions
        self._a_new = self._create_action("&New", "Ctrl+n")
        self._a_new.triggered.connect(self.new_file)
        self._a_newblank = self._create_action("New &Blank", "Ctrl+Shift+n")
        self._a_newblank.triggered.connect(self.new_blank_file)
        self._a_open = self._create_action("&Open...", "Ctrl+o")
        self._a_open.triggered.connect(self.open_file)
        self._a_reload = self._create_action("&Reload", "F5")
        self._a_reload.triggered.connect(self.reload_file)
        self._a_reload.setDisabled(True)
        self._a_save = self._create_action("&Save", "Ctrl+s")
        self._a_save.triggered.connect(self.save_file)
        self._a_saveas = self._create_action("Save &As...", "Ctrl+Shift+s")
        self._a_saveas.triggered.connect(self.save_file_as)
        self._a_casebook = self._create_action("Create E&xcel", "Ctrl+Shift+x")
        self._a_casebook.triggered.connect(self.create_casebook)
        self._a_clear = self._create_action("&Clear Console", "Ctrl+Shift+c")
        self._a_clear.triggered.connect(self.console.clear)
        self._a_quit = self._create_action("&Quit", "Ctrl+q")
        self._a_quit.triggered.connect(self.close)

        # Edit actions in addition to those provided by the editor
        self._a_activity = self._create_action("&Activity", "Ctrl+Alt+a")
        self._a_activity.triggered.connect(self.insert_activity)
        self._a_award = self._create_action("Awar&d", "Ctrl+Alt+d")
        self._a_award.triggered.connect(self.insert_award)
        self._a_edu = self._create_action("&Education", "Ctrl+Alt+e")
        self._a_edu.triggered.connect(self.insert_education)
        self._a_skills = self._create_action("&Skillset", "Ctrl+Alt+s")
        self._a_skills.triggered.connect(self.insert_skillset)
        self._a_test = self._create_action("&Test", "Ctrl+Alt+t")
        self._a_test.triggered.connect(self.insert_test)

        # LaTeX actions
        self._a_parse = self._create_action("&Parse", "Ctrl+`")
        self._a_parse.triggered.connect(self.show_parse_tree)
        self._a_parse.setToolTip("Show the parse tree in the console")
        self._a_runlatex = self._create_action("&Run", "Ctrl+r")
        self._a_runlatex.triggered.connect(self.run_latex)
        self._a_impsettings = self._create_action("&Import Settings...", "Ctrl+i")
        self._a_impsettings.triggered.connect(self.import_settings)
        self._a_impsettings.setToolTip("Load LaTeX settings from a file")
        self._a_expsettings = self._create_action("&Export Settings...", "Ctrl+Shift+e")
        self._a_expsettings.triggered.connect(self.export_settings)
        self._a_expsettings.setToolTip("Save current LaTeX settings to a file")
        self._a_restoredefault = self._create_action("Restore &Default", "Ctrl+Shift+d")
        self._a_restoredefault.triggered.connect(self.restore_default)
        self._a_restoredefault.setToolTip("Restore default LaTeX settings")

        # Editor options
        self._a_largerfont = self._create_action("&Larger Font", "Ctrl+=")
        self._a_largerfont.triggered.connect(self.increment_editor_font_size)
        self._a_smallerfont = self._create_action("&Smaller Font", "Ctrl+-")
        self._a_smallerfont.triggered.connect(self.decrement_editor_font_size)
        self._a_togglewrap = self._create_action("&Wrap Lines", "Alt+z")
        self._a_togglewrap.triggered.connect(self.toggle_wrap)
        self._a_togglewrap.setCheckable(True)
        self._a_toggleopenpdf = self._create_action("Open &PDF When Done", "Alt+p")
        self._a_toggleopenpdf.triggered.connect(self.toggle_open_pdf)
        self._a_toggleopenpdf.setCheckable(True)
        self._a_configdialog = self._create_action("&More...", "Ctrl+,")
        self._a_configdialog.triggered.connect(self.open_config_dialog)

        # Chat options
        self._a_enterprompt = self._create_action("&Enter Prompt...", "Ctrl+e")
        self._a_enterprompt.triggered.connect(self._show_prompt_window)
        self._a_reset_chat = self._create_action("&Reset Context", "Ctrl+Shift+r")
        self._a_reset_chat.triggered.connect(self.reset_chat_context)
        self._a_paramsdialog = self._create_action("&Parameters...", "Ctrl+p")
        self._a_paramsdialog.triggered.connect(self._params_window.exec)

        self._gpt_actions = self._create_gpt_actions()

        self._create_menus()
        self._update_ui_with_config()

        self.editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self.show_context_menu)

        # Set window properties
        self.setGeometry(
            self._config.window_x,
            self._config.window_y,
            self._config.window_width,
            self._config.window_height,
        )
        central_widget.setSizes([680, 320])
        editor_panel.setSizes([450, 150])

        self.new_file()
        self._load_initial_settings()

    def _get_config(self):
        try:
            return Config.from_json(LAST_USED_CONFIG)
        except (FileNotFoundError, json.JSONDecodeError):
            return Config()

    def _create_action(self, text: str, shortcut: str) -> QAction:
        action = QAction(text, self)
        action.setShortcut(shortcut)
        return action

    def _create_menus(self):
        # File menu
        file_menu = QMenu("&File", self)
        file_menu.setToolTipsVisible(True)
        self._menubar.addMenu(file_menu)

        file_menu.addAction(self._a_new)
        file_menu.addAction(self._a_newblank)
        file_menu.addSeparator()
        file_menu.addAction(self._a_open)
        file_menu.addAction(self._a_reload)
        file_menu.addSeparator()
        file_menu.addAction(self._a_save)
        file_menu.addAction(self._a_saveas)
        file_menu.addAction(self._a_casebook)
        file_menu.addSeparator()
        file_menu.addAction(self._a_clear)
        file_menu.addAction(self._a_quit)

        # Edit menu
        edit_menu = QMenu("&Edit", self)
        edit_menu.setToolTipsVisible(True)
        self._menubar.addMenu(edit_menu)

        edit_menu.addAction(self.editor.undo_action)
        edit_menu.addAction(self.editor.redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.editor.cut_action)
        edit_menu.addAction(self.editor.copy_action)
        edit_menu.addAction(self.editor.paste_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.editor.selectall_action)
        # edit_menu.addAction(self._a_goto)
        edit_menu.addAction(self.editor.find_action)
        edit_menu.addAction(self.editor.replace_action)
        edit_menu.addSeparator()

        insertion_menu = QMenu("&Insert", self)
        edit_menu.addMenu(insertion_menu)
        insertion_menu.addAction(self._a_activity)
        insertion_menu.addAction(self._a_award)
        insertion_menu.addAction(self._a_edu)
        insertion_menu.addAction(self._a_skills)
        insertion_menu.addAction(self._a_test)

        # ChatGPT menu
        self._gpt_menu = self._create_gpt_menu()
        self._menubar.addMenu(self._gpt_menu)

        # LaTeX menu
        latex_menu = QMenu("La&TeX", self)
        latex_menu.setToolTipsVisible(True)
        self._menubar.addMenu(latex_menu)

        latex_menu.addAction(self._a_parse)
        latex_menu.addAction(self._a_runlatex)
        latex_menu.addSeparator()
        latex_menu.addAction(self._a_impsettings)
        latex_menu.addAction(self._a_expsettings)
        latex_menu.addAction(self._a_restoredefault)

        # Options menu
        options_menu = QMenu("&Options", self)
        options_menu.setToolTipsVisible(True)
        self._menubar.addMenu(options_menu)

        options_menu.addAction(self._a_largerfont)
        options_menu.addAction(self._a_smallerfont)
        options_menu.addSeparator()
        options_menu.addAction(self._a_togglewrap)
        options_menu.addAction(self._a_toggleopenpdf)
        options_menu.addSeparator()
        options_menu.addAction(self._a_configdialog)

    def show_context_menu(self, position):
        context_menu = self.editor.createStandardContextMenu()
        context_menu.addSeparator()

        # insertion actions
        context_insertion_menu = QMenu("Insert", self)
        context_menu.addMenu(context_insertion_menu)
        context_insertion_menu.addAction(self._a_activity)
        context_insertion_menu.addAction(self._a_edu)
        context_insertion_menu.addAction(self._a_skills)
        context_insertion_menu.addAction(self._a_test)
        context_insertion_menu.addAction(self._a_award)
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
        actions.append(self._a_reset_chat)
        actions.append(self._a_paramsdialog)
        return actions

    def _create_gpt_menu(self) -> QMenu:
        menu = QMenu("&ChatGPT", self)
        for i, action in enumerate(self._gpt_actions):
            # add a separator just above each of the listed actions
            if i and action in [self._a_enterprompt, self._a_paramsdialog]:
                menu.addSeparator()
            menu.addAction(action)
        # if the chat module fails to find an appropriate settings file
        if not chat.openai.api_key:
            for action in menu.actions():
                action.setDisabled(True)
        return menu

    def _exec_prompt(self, prompt_head: str, parent=None):
        prompt_tail = self.editor.get_selected()
        prompt = f"{prompt_head}\n\n{prompt_tail}".strip()
        promt_timestamp = timestamp()

        if not prompt:
            show_error(parent=parent or self, text="The prompt must not be empty.")
            return

        thread = ChatThread(gpt=self._gpt, prompt=prompt, params=self._chat_params)
        # Must keep a reference to the thread and not delete it
        # prematurely, but it should be deleted eventually.
        # The most simple and robust solution seems to be holding threads
        # in a list and and delete the old one when a new one is created
        try:
            self._chat_threads.pop()  # delete the old one if exists
        except IndexError:
            pass
        self._chat_threads.append(thread)

        thread.waiting.connect(self._signal_wait)
        thread.progress.connect(self._stream_completion)
        thread.wait_finished.connect(self.console.remove_line)

        def _on_completion_success():
            self.console.xappend("")
            tokens_used = self._gpt.token_count(self._chat_params.model)
            self._console_log(f">>> {tokens_used}/{chat.MAX_TOKENS}")
            self.console.xappend("")
            self._set_gpt_enabled(True)
            # save the prompt and the completion
            try:
                completion = self._gpt.messages[-1]["content"]
                self.write_chat_history(
                    (promt_timestamp, "user", prompt),
                    (timestamp(), "assistant", completion),
                )
            except Exception as e:
                self._handle_exc(e)
            finally:
                thread.quit()

        thread.finished.connect(_on_completion_success)

        def _on_completion_error(e: Exception):
            self._handle_exc(e, parent=parent)
            self._set_gpt_enabled(True)
            thread.quit()

        thread.error.connect(_on_completion_error)

        self._set_gpt_enabled(False)
        self.console.xappend(f">>> Prompt", weight=700)
        self.console.xappend(prompt)
        self.console.xappend("")
        self.console.xappend(f">>> {self._chat_params.model}", weight=700)
        self.console.xappend("")

        if not os.path.isdir("chat_history"):
            os.mkdir("chat_history")
        if self._chat_history is None:
            self._chat_history = os.path.join("chat_history", f"chat_{timestamp()}.csv")
            self.write_chat_history((timestamp(), "system", self._gpt.system_message))

        thread.start()

    def _signal_wait(self, signal: str):
        self.console.insertPlainText(signal)
        self._wait_count += 1
        if self._wait_count > 5:
            self.console.remove_line()
            self._wait_count = 0
        self.console.ensureCursorVisible()

    def _stream_completion(self, content: str):
        self.console.insertPlainText(content)
        self.console.ensureCursorVisible()

    def _set_gpt_enabled(self, enabled: bool = True):
        self._gpt_menu.setEnabled(enabled)
        self._prompt_window.send_button.setEnabled(enabled)

    def write_chat_history(self, *rows):
        with open(self._chat_history, mode="a", newline="", encoding="utf-8") as f:
            csv_writer = csv.writer(f)
            for row in rows:
                csv_writer.writerow(row)

    def _update_ui_with_config(self):
        # editor font and line wrap
        editor_font = QFont(self._config.editor_font, self._config.editor_font_size)
        self.editor.setFont(editor_font)
        if self._config.editor_wrap_lines:
            self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # editor foreground & background
        editor_fg = f"color: {self._config.editor_foreground};"
        editor_bg = f"background: {self._config.editor_background};"
        self.editor.setStyleSheet(
            f"#editor {{{editor_fg} {editor_bg}}} "
            f"#editor:focus {{{editor_fg} {editor_bg}}}"
        )

        # console font and line wrap
        console_font = QFont(self._config.console_font, self._config.console_font_size)
        self.console.setFont(console_font)
        if self._config.console_wrap_lines:
            self.console.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.console.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

        # console foreground & background
        console_fg = f"color: {self._config.console_foreground};"
        console_bg = f"background: {self._config.console_background};"
        self.console.setStyleSheet(
            f"#console {{{console_fg} {console_bg}}} "
            f"#console:focus {{{console_fg} {console_bg}}}"
        )

        # menu items
        self._a_togglewrap.setChecked(self._config.editor_wrap_lines)
        self._a_toggleopenpdf.setChecked(self._config.open_pdf_when_done)

        # syntax highlighting
        # TODO make configurable
        highlighter = self.editor.highlighter
        highlighter.update_format(
            highlighter.DEFAULT,
            foreground=self._config.cv_default_foreground,
        )
        highlighter.update_format(
            highlighter.KEYWORD,
            foreground=self._config.cv_keyword_foreground,
            bold=self._config.cv_keyword_bold,
        )
        highlighter.update_format(
            highlighter.BULLET,
            foreground=self._config.cv_bullet_foreground,
            bold=self._config.cv_bullet_bold,
        )
        highlighter.update_format(
            highlighter.DATE,
            foreground=self._config.cv_date_foreground,
            bold=self._config.cv_date_bold,
        )
        highlighter.update_format(
            highlighter.SECTION,
            foreground=self._config.cv_section_foreground,
            bold=self._config.cv_section_bold,
        )
        highlighter.update_format(
            highlighter.UNKNOWN,
            foreground=self._config.cv_unknown_foreground,
            bold=self._config.cv_unknown_bold,
        )

    def _load_initial_settings(self):
        try:
            settings = tex.Settings.from_json(LAST_USED_SETTINGS)
        except (FileNotFoundError, json.JSONDecodeError):
            settings = tex.Settings()
        self.settings_frame.load_settings(settings)

    def closeEvent(self, event: QCloseEvent):
        if self.isWindowModified():
            # Ask user to handle unsaved change
            q = "Your document has unsaved changes.\nDiscard the changes and close the program?"
            msg_box = QMessageBox(parent=self, text=q)
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setWindowTitle(APP_TITLE)
            _ = QMessageBox.StandardButton
            msg_box.setStandardButtons(_.Yes | _.No)
            msg_box.setDefaultButton(_.Yes)
            if msg_box.exec() == _.No:
                event.ignore()

        else:
            # Save current LaTeX settings
            settings = self.settings_frame.get_settings()
            if not os.path.isdir(SETTINGS_DIR):
                os.mkdir(SETTINGS_DIR)
            json_dump(settings, filepath=LAST_USED_SETTINGS)

            # Save current config; with update window geometry too
            window_rect = self.geometry()
            self._config.window_x = window_rect.x()
            self._config.window_y = window_rect.y()
            self._config.window_width = window_rect.width()
            self._config.window_height = window_rect.height()
            if not os.path.isdir(CONFIG_DIR):
                os.mkdir(CONFIG_DIR)
            json_dump(self._config, filepath=LAST_USED_CONFIG)

            # Close the prompt window if open
            self._prompt_window.close()
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
        # self.console.clear()
        try:
            template_path = "templates/classic.tex"
            tex_path = "output/output.tex"

            if not os.path.isdir("output"):
                os.mkdir("output")

            cv, _ = txtparse.parse(self.editor.toPlainText())
            settings = self.settings_frame.get_settings()
            rendered = tex.render(template_path=template_path, cv=cv, settings=settings)
            with open(tex_path, "w", encoding="utf-8") as tex_file:
                tex_file.write(rendered)

            process = QProcess(self)
            process.readyReadStandardOutput.connect(self._handle_latex_output)
            process.finished.connect(self._handle_latex_finish)
            process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
            process.start("lualatex", ["-interaction=nonstopmode", tex_path])

        except Exception as e:
            self._handle_exc(e)

    def _handle_latex_output(self):
        process = self.sender()
        output = process.readAllStandardOutput().data().decode()
        self.console.insertPlainText(output)
        self.console.ensureCursorVisible()

    def _handle_latex_finish(self, exit_code, exit_status):
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

        self.console.xappend("Operation completed successfully.", weight=700)
        self.console.xappend("")

        basename = f"output_{timestamp()}.pdf"
        # TODO may allow user to specify default output dir
        dest_path = os.path.join("output", basename)
        try:
            if not os.path.isdir("output"):
                os.mkdir("output")
            if os.path.isfile(dest_path):
                os.remove(dest_path)
            os.rename("output.pdf", dest_path)
            if self._config.open_pdf_when_done:
                os.startfile(dest_path)
        except Exception as e:
            self._handle_exc(e)

    def create_casebook(self):
        cv, _ = txtparse.parse(self.editor.toPlainText())
        basename = f"case_{timestamp()}.xlsx"
        dest_path = os.path.join("output", basename)
        thread = ExcelThread(cv=cv)
        error = False

        try:
            self._excel_threads.pop()
        except IndexError:
            pass
        self._excel_threads.append(thread)

        thread.started.connect(lambda: self._console_log("Creating Excel..."))
        thread.progress.connect(self._console_log)

        def _on_excel_success(wb: excel.Workbook):
            if not os.path.isdir("output"):
                os.mkdir("output")
            wb.save(dest_path)
            os.startfile(dest_path)
            self._a_casebook.setEnabled(True)
            thread.quit()

        thread.completed.connect(_on_excel_success)

        def _on_excel_error(e: Exception):
            # show error once only
            nonlocal error
            if error:
                return
            self._handle_exc(e)
            self._a_casebook.setEnabled(True)
            thread.quit_subthreads()
            thread.quit()
            error = True

        thread.error.connect(_on_excel_error)

        self._a_casebook.setDisabled(True)
        thread.start()

    def _handle_exc(self, e: Exception, parent=None):
        self.console.xappend(
            traceback.format_exc(),
            color=self._config.console_error_foreground,
        )
        show_error(parent=parent or self, text=f"{e.__class__.__name__}\n\n{e}")

    def _update_filepath(self):
        if self._filepath:
            filename = os.path.basename(self._filepath)
            self._a_reload.setDisabled(False)
            font_metrics = QFontMetrics(self._a_reload.font())
            path_text = font_metrics.elidedText(
                filename, Qt.TextElideMode.ElideMiddle, 150
            )
            self._a_reload.setText(f"Reload {path_text}")
            basename, _ = os.path.splitext(filename)
        else:
            basename = "untitled"
            self._a_reload.setDisabled(True)
            self._a_reload.setText("Reload")
        self.setWindowTitle(f"{basename}[*] - {APP_TITLE}")
        self.setWindowFilePath(self._filepath)

    def _on_editor_change(self):
        self.setWindowModified(self.document.isModified())

    def _console_log(self, text: str):
        self.console.xappend(text, color=self._config.console_log_foreground)

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
            _, ext = os.path.splitext(filepath)
            if ext.lower() in [".docx", ".doc"]:
                text = docparse.parse(filepath)
            else:
                text = open(filepath, encoding="utf-8").read()
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
            filter="Text or Word Files (*.txt *.docx *.doc)",
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
        base, ext = os.path.splitext(self._filepath)
        if ext.lower() in [".docx", ".doc"]:
            self.save_file_as(default_filename=f"{base}.txt")
            return
        try:
            self._save_file(self._filepath)
        except Exception as e:
            self._handle_exc(e)

    def save_file_as(self, *, default_filename=""):
        default_path = os.path.join(self._config.default_save_dir, default_filename)
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            caption="Save File",
            directory=default_path,
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
        json_dump(settings, filepath=filepath)

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

    def toggle_open_pdf(self, state: bool):
        self._config.open_pdf_when_done = state
        self._update_ui_with_config()

    def open_config_dialog(self):
        w = ConfigDialog(self)
        w.setWindowTitle("Options")
        w.load_config(self._config)

        def _update_config():
            try:
                self._config = w.get_config()
                self._update_ui_with_config()
            except Exception as e:
                self._handle_exc(e)
            finally:
                w.close()

        w.ok_button.clicked.connect(_update_config)
        w.exec()

    def _decorate_params_dialog(self):
        self._params_window.setWindowTitle("Chat Completion Parameters")
        self._params_window.setGeometry(
            self._config.window_x + 40, self._config.window_y + 40, 480, 600
        )
        self._params_window.load_params(self._chat_params)
        self._params_window.ok_button.clicked.connect(self._update_chat_params)

    def _update_chat_params(self):
        try:
            self._chat_params = self._params_window.get_params()
        except Exception as e:
            self._handle_exc(e)
        finally:
            self._params_window.close()

    def _show_prompt_window(self):
        self._prompt_window.show()
        self._prompt_window.raise_()

    def _send_prompt(self):
        self.raise_()
        self._prompt_window.raise_()
        prompt_head = self._prompt_window.get_prompt()
        self._exec_prompt(prompt_head, parent=self._prompt_window)

    def reset_chat_context(self):
        self._gpt.reset_messages()
        show_info(parent=self, text="Chat context has been reset.")


class GptWindow(QDialog):
    def __init__(self):
        super().__init__(None, Qt.WindowType.Window)
        self.send_action = QAction(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.editor = QPlainTextEdit(self)
        self.editor.setFrameShape(QFrame.Shape.NoFrame)
        self.editor.document().setDocumentMargin(6)
        layout.addWidget(self.editor)

        button_frame = QFrame(self)
        layout.addWidget(button_frame)
        button_frame_layout = QHBoxLayout()
        button_frame.setLayout(button_frame_layout)
        self.send_button = QPushButton("Send", self)
        self.send_button.clicked.connect(self.send_action.trigger)
        self.send_button.setToolTip("Alternatively, press Ctrl+Return")
        button_frame_layout.addWidget(
            self.send_button, alignment=Qt.AlignmentFlag.AlignRight
        )

        # trigger self.run_action with ctrl+return
        self.addAction(self.send_action)
        self.send_action.setShortcut("Ctrl+Return")

    def get_prompt(self):
        return self.editor.toPlainText()


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

        layout.addWidget(QLabel("Console Font"))
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
        self.ok_button = QPushButton("OK", self)
        button_frame_layout.addWidget(
            self.ok_button, alignment=Qt.AlignmentFlag.AlignRight
        )

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


class ParamsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.setLayout(layout)
        spacer20 = QSpacerItem(0, 20)
        spacer10 = QSpacerItem(0, 10)

        params_frame = QFrame(self)
        layout.addWidget(params_frame)
        self._params_layout = QGridLayout()
        self._params_layout.setHorizontalSpacing(15)
        self._params_layout.setVerticalSpacing(5)
        params_frame.setLayout(self._params_layout)
        self._params_layout.setColumnStretch(0, 0)
        self._params_layout.setColumnStretch(1, 1)

        # model
        row = 0
        self._params_layout.addWidget(QLabel("<b>Model</b>"), row, 0)
        self.model_selector = QComboBox(self)
        self.model_selector.addItems(["gpt-3.5-turbo", "gpt-4"])
        self.model_selector.setDisabled(True)
        self._params_layout.addWidget(self.model_selector, row + 1, 0)

        row += 2
        self._params_layout.addItem(spacer20, row, 0)

        # temperature
        row += 1
        self._params_layout.addWidget(QLabel("<b>Temperature</b>"), row, 0)

        self.temperature_check = QCheckBox("Use Default", self)
        self._params_layout.addWidget(self.temperature_check, row + 1, 0)
        self.temperature_selector = QDoubleSpinBox(self)
        self.temperature_selector.setMinimum(0.0)
        self.temperature_selector.setMaximum(2.0)
        self.temperature_selector.setSingleStep(0.1)
        self._params_layout.addWidget(self.temperature_selector, row + 2, 0)
        temperature_standin = QLabel()
        self._params_layout.addWidget(temperature_standin, row + 2, 0)

        self._create_explanation(
            row,
            "What sampling temperature to use, between 0 and 2. "
            "Higher values like 0.8 will make the output more random, "
            "while lower values like 0.2 will make it more focused and deterministic. "
            "OpenAI remcommends that you alter this value or <b>top p</b> but not both.",
        )

        row += 5
        self._params_layout.addItem(spacer10, row, 0)

        # top_p
        row += 1
        self._params_layout.addWidget(QLabel("<b>Top P</b>"), row, 0)

        self.top_p_check = QCheckBox("Use Default", self)
        self._params_layout.addWidget(self.top_p_check, row + 1, 0)
        self.top_p_selector = QDoubleSpinBox(self)
        self.top_p_selector.setMinimum(0.0)
        self.top_p_selector.setMaximum(1.0)
        self.top_p_selector.setSingleStep(0.1)
        self._params_layout.addWidget(self.top_p_selector, row + 2, 0)
        top_p_standin = QLabel()
        self._params_layout.addWidget(top_p_standin, row + 2, 0)

        self._create_explanation(
            row,
            "An alternative to sampling with temperature, "
            "where the model considers the results of the tokens with <b>top p</b> probability mass. "
            "So 0.1 means only the tokens comprising the top 10% probability mass are considered. "
            "OpenAI recommends that you alter this value or <b>temperature</b> but not both.",
        )

        row += 5
        self._params_layout.addItem(spacer10, row, 0)

        # presence penalty
        row += 1
        self._params_layout.addWidget(QLabel("<b>Presence Penalty</b>"), row, 0)

        self.pres_penalty_check = QCheckBox("Use Default", self)
        self._params_layout.addWidget(self.pres_penalty_check, row + 1, 0)
        self.pres_penalty_selector = QDoubleSpinBox(self)
        self.pres_penalty_selector.setMinimum(-2.0)
        self.pres_penalty_selector.setMaximum(2.0)
        self.pres_penalty_selector.setSingleStep(0.1)
        self._params_layout.addWidget(self.pres_penalty_selector, row + 2, 0)
        pres_penalty_standin = QLabel()
        self._params_layout.addWidget(pres_penalty_standin, row + 2, 0)

        self._create_explanation(
            row,
            "Number between -2.0 and 2.0. Positive values penalize new tokens "
            "based on whether they appear in the text so far, "
            "increasing the model's likelihood to talk about new topics.",
        )

        row += 5
        self._params_layout.addItem(spacer10, row, 0)

        # frequency penalty
        row += 1
        self._params_layout.addWidget(QLabel("<b>Frequency Penalty</b>"), row, 0)

        self.freq_penalty_check = QCheckBox("Use Default", self)
        self._params_layout.addWidget(self.freq_penalty_check, row + 1, 0)
        self.freq_penalty_selector = QDoubleSpinBox(self)
        self.freq_penalty_selector.setMinimum(-2.0)
        self.freq_penalty_selector.setMaximum(2.0)
        self.freq_penalty_selector.setSingleStep(0.1)
        self._params_layout.addWidget(self.freq_penalty_selector, row + 2, 0)
        freq_penalty_standin = QLabel()
        self._params_layout.addWidget(freq_penalty_standin, row + 2, 0)

        self._create_explanation(
            row,
            "Number between -2.0 and 2.0. Positive values penalize new tokens "
            "based on their existing frequency in the text so far, "
            "decreasing the model's likelihood to repeat the same line verbatim.",
        )

        # link check states to selectors
        self.temperature_check.stateChanged.connect(
            lambda: self._toggle_selector(
                self.temperature_check,
                self.temperature_selector,
                temperature_standin,
            )
        )
        self.top_p_check.stateChanged.connect(
            lambda: self._toggle_selector(
                self.top_p_check, self.top_p_selector, top_p_standin
            )
        )
        self.pres_penalty_check.stateChanged.connect(
            lambda: self._toggle_selector(
                self.pres_penalty_check,
                self.pres_penalty_selector,
                pres_penalty_standin,
            )
        )
        self.freq_penalty_check.stateChanged.connect(
            lambda: self._toggle_selector(
                self.freq_penalty_check,
                self.freq_penalty_selector,
                freq_penalty_standin,
            )
        )

        # ok button
        button_frame = QFrame(self)
        layout.addWidget(button_frame)
        button_frame_layout = QHBoxLayout()
        button_frame.setLayout(button_frame_layout)
        self.ok_button = QPushButton("OK", self)
        button_frame_layout.addWidget(
            self.ok_button, alignment=Qt.AlignmentFlag.AlignRight
        )

    def _create_explanation(self, row: int, text: str):
        label = QLabel(f'<span style="color: #696969;">{text}</span>')
        label.setWordWrap(True)
        self._params_layout.addWidget(label, row, 1, 4, 1)  # span 3 rows
        # allow the 2nd and 4th row to expand
        self._params_layout.setRowStretch(row + 1, 1)
        self._params_layout.setRowStretch(row + 3, 1)
        self._params_layout.setAlignment(label, Qt.AlignmentFlag.AlignTop)

    def _toggle_selector(
        self, checkbox: QCheckBox, selector: QDoubleSpinBox, standin: QLabel
    ):
        if checkbox.isChecked():
            selector.hide()
            standin.show()
        else:
            standin.hide()
            selector.show()

    def get_params(self):
        params = chat.Params()
        params.model = self.model_selector.currentText()
        if not self.temperature_check.isChecked():
            params.temperature = self.temperature_selector.value()
        if not self.top_p_check.isChecked():
            params.top_p = self.top_p_selector.value()
        if not self.pres_penalty_check.isChecked():
            params.presence_penalty = self.pres_penalty_selector.value()
        if not self.freq_penalty_check.isChecked():
            params.frequency_penalty = self.freq_penalty_selector.value()
        return params

    def load_params(self, params: chat.Params):
        self.model_selector.setCurrentText(params.model)

        if params.temperature is None:
            self.temperature_check.setChecked(True)
        else:
            self.temperature_check.setChecked(False)
            self.temperature_selector.setValue(params.temperature)

        if params.top_p is None:
            self.top_p_check.setChecked(True)
        else:
            self.top_p_check.setChecked(False)
            self.top_p_selector.setValue(params.top_p)

        if params.presence_penalty is None:
            self.pres_penalty_check.setChecked(True)
        else:
            self.pres_penalty_check.setChecked(False)
            self.pres_penalty_selector.setValue(params.presence_penalty)

        if params.frequency_penalty is None:
            self.freq_penalty_check.setChecked(True)
        else:
            self.freq_penalty_check.setChecked(False)
            self.freq_penalty_selector.setValue(params.frequency_penalty)


class LatexSettingsFrame(QFrame):
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

        layout.addWidget(QLabel("Handle Ending Periods"))
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

        layout.addWidget(Separator(self))
        layout.addSpacing(space_after_separator)

        # page numbers
        self.page_numbers_check = QCheckBox("Show Page Numbers", self)
        layout.addWidget(self.page_numbers_check)
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

        s.show_page_numbers = self.page_numbers_check.isChecked()

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

        self.page_numbers_check.setChecked(s.show_page_numbers)


class LatexPaperSelector(QComboBox):
    _text_to_paper = {
        "A4": "a4paper",
        "Letter": "letterpaper",
    }
    _paper_to_text = {v: k for k, v in _text_to_paper.items()}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.addItems(sorted(self._text_to_paper))

    def get_paper(self):
        return self._text_to_paper[self.currentText()]

    def set_from_paper(self, paper: str):
        self.setCurrentText(self._paper_to_text[paper])


class LatexFontSizeSelector(QSpinBox):
    _commands = [
        "normalsize",
        "large",
        "Large",
        "LARGE",
        "huge",
        "Huge",
    ]
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
    for _style in [
        "american",
        "american long",
        "american slash",
        "british",
        "british long",
        "british slash",
        "iso",
        "yyyy/mm/dd",
    ]:
        _key = tex.format_date(_sample_date, style=_style)
        _sample_to_style[_key] = _style

    del _style
    del _key

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


class Console(QTextEdit):
    # handles process outputs and supports auto-scrolling

    def xappend(self, text: str, weight=400, color: str = ""):
        # to work around the problem of append() inserting at the position
        # of the cursor instead of the end of the document

        # setCharFormat necessary to prevent the inserted content inheriting
        # the style at the cursor position
        char_format = QTextCharFormat()
        char_format.setFontWeight(weight)
        if color:
            char_format.setForeground(QColor(color))

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.setCharFormat(char_format)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        self.append(text)
        self.ensureCursorVisible()

    def remove_line(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.movePosition(
            QTextCursor.MoveOperation.StartOfLine,
            QTextCursor.MoveMode.KeepAnchor,
        )
        cursor.removeSelectedText()


class ChatThread(QThread):
    waiting = pyqtSignal(str)
    progress = pyqtSignal(str)
    wait_finished = pyqtSignal()
    finished = pyqtSignal()
    error = pyqtSignal(Exception)

    def __init__(
        self,
        gpt: chat.Chat,
        prompt: str,
        params: chat.Params,
        parent=None,
    ):
        super().__init__(parent)
        self.gpt = gpt
        self.prompt = prompt
        self.params = params
        self.wait_thread = ChatWaitThread()

    def run(self):
        self.wait_thread.waiting.connect(self._signal_wait)
        self.wait_thread.start()
        waiting = True

        kwargs = {"model": self.params.model, "stream": True}
        if self.params.temperature is not None:
            kwargs["temperature"] = self.params.temperature
        if self.params.top_p is not None:
            kwargs["top_p"] = self.params.top_p
        if self.params.presence_penalty is not None:
            kwargs["presence_penalty"] = self.params.presence_penalty
        if self.params.frequency_penalty is not None:
            kwargs["frequency_penalty"] = self.params.frequency_penalty
        try:
            for content in self.gpt.send(self.prompt, keep_context=True, **kwargs):
                # upon receiving the first response, stop sending the wait signal
                if waiting:
                    self._on_wait_finish()
                    waiting = False
                self.progress.emit(content)
        except Exception as e:
            if waiting:
                self._on_wait_finish()
            self.error.emit(e)
        else:
            self.finished.emit()

    def _signal_wait(self):
        self.waiting.emit(". ")

    def _on_wait_finish(self):
        self.wait_thread.waiting.disconnect(self._signal_wait)
        self.wait_thread.quit()
        self.wait_finished.emit()
        time.sleep(0.1)  # allow app some time to clean up


class ChatWaitThread(QThread):
    # run while the chat thread is waiting for response
    waiting = pyqtSignal()

    def run(self):
        waittime = 0
        interval = 0.5
        while True:
            if waittime > 40:
                return
            self.waiting.emit()
            time.sleep(interval)
            waittime += interval


class ExcelThread(QThread):
    progress = pyqtSignal(str)
    completed = pyqtSignal(excel.Workbook)
    error = pyqtSignal(Exception)

    def __init__(self, cv: txtparse.CV, parent=None):
        super().__init__(parent)
        self.cv = cv

        self._activity_translators = []
        for i, act in enumerate(cv.activities):
            role_translator = Translator(act.role, id=("role", i))
            self._activity_translators.append(role_translator)
            org_translator = Translator(act.org, id=("org", i))
            self._activity_translators.append(org_translator)
            descr_translator = Translator(
                " ".join(act.descriptions), id=("descriptions", i)
            )
            self._activity_translators.append(descr_translator)
        for thread in self._activity_translators:
            thread.result_ready.connect(self._handle_activity_result)
            thread.error.connect(self.error.emit)

        self._award_translators = []
        for i, award in enumerate(cv.awards):
            award_translator = Translator(award.name, id=i)
            award_translator.result_ready.connect(self._handle_award_result)
            award_translator.error.connect(self.error.emit)
            self._award_translators.append(award_translator)

        self._finished = []

    def run(self):
        # emite completed() if there is no runnable thread
        self._check_completion()
        for thread in self._activity_translators:
            thread.start()
        for thread in self._award_translators:
            thread.start()

    def _handle_activity_result(self, result: tuple):
        text, (field, index) = result
        act = self.cv.activities[index]
        # `description` field calls for a list of strings
        setattr(act, field, [text] if field == "descriptions" else text)
        self._mark_finished(self.sender(), self._activity_translators)
        self._check_completion()

    def _handle_award_result(self, result: tuple):
        text, index = result
        self.cv.awards[index].name = text
        self._mark_finished(self.sender(), self._award_translators)
        self._check_completion()

    def _mark_finished(self, thread: "Translator", thread_pool: list):
        self.progress.emit(f"Translated: {thread.text}")
        thread_pool.remove(thread)
        self._finished.append(thread)

    def _check_completion(self):
        if self._activity_translators or self._award_translators:
            return
        wb = excel.create_casebook(self.cv)
        self.completed.emit(wb)

    def quit_subthreads(self):
        for thread in self._activity_translators:
            thread.quit()
        for thread in self._award_translators:
            thread.quit()


class Translator(QThread):
    result_ready = pyqtSignal(tuple)
    error = pyqtSignal(Exception)

    def __init__(self, text, id=None, parent=None):
        super().__init__(parent)
        self.text = text
        self.id = id

    def run(self):
        if not self.text:
            self.result_ready.emit(("", self.id))
            return
        gpt = chat.Chat(system_message="You are a translator of student resumes.")
        prompt = (
            f"Please translate the resume fragment below into Chinese. "
            f"If it contains Markdown formatting, remove the formatting. "
            f"Reply with the translated text only.\n\n{self.text}"
        )
        try:
            response = []
            for chunk in gpt.send(
                prompt=prompt,
                keep_context=False,
                model="gpt-3.5-turbo",
            ):
                response.append(chunk)
            self.result_ready.emit(("".join(response), self.id))
        except Exception as e:
            self.error.emit(e)


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


def json_dump(data, filepath: str, indent=4):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(dataclasses.asdict(data), f, indent=indent)


def timestamp() -> str:
    now = datetime.datetime.now()
    return now.strftime("%y-%m-%d_%H%M%S")
