import sys
import os
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QPlainTextEdit, QSplitter,
    QTreeView, QFileDialog, QWidget, QTextEdit
)
from PyQt6.QtGui import (
    QIcon, QFont, QFileSystemModel, QAction, QPainter, QColor, QTextFormat,
    QSyntaxHighlighter, QTextCharFormat
)
from PyQt6.QtCore import Qt, QSize, QRect

# -----------------------------
# Line Number Area
# -----------------------------
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)

# -----------------------------
# Code Editor with Line Numbers
# -----------------------------
class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)

    def line_number_area_width(self):
        digits = 1
        max_value = max(1, self.blockCount())
        while max_value >= 10:
            max_value //= 10
            digits += 1
        space = 20 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#2c2c2c")
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#252526"))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#858585"))
                painter.drawText(0, top, self.line_number_area.width() - 8, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

# -----------------------------
# Python Syntax Highlighter
# -----------------------------
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self._highlighting_rules = []

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
            'elif', 'else', 'except', 'finally', 'for', 'from', 'global',
            'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or',
            'pass', 'raise', 'return', 'try', 'while', 'with', 'yield'
        ]
        for word in keywords:
            pattern = re.compile(r'\b' + word + r'\b')
            self._highlighting_rules.append((pattern, keyword_format))

        # Built-in functions
        builtin_format = QTextCharFormat()
        builtin_format.setForeground(QColor("#C586C0"))
        builtins = [
            'print', 'len', 'range', 'open', 'input', 'int', 'str', 'list', 'dict', 'set',
            'tuple', 'type', 'super', 'isinstance', 'dir', 'enumerate', 'zip', 'map', 'filter', 'sum'
        ]
        for word in builtins:
            pattern = re.compile(r'\b' + word + r'\b')
            self._highlighting_rules.append((pattern, builtin_format))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))
        self._highlighting_rules.append((re.compile(r'#.*'), comment_format))

        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))
        self._highlighting_rules.append((re.compile(r'"""[\s\S]*?"""'), string_format))
        self._highlighting_rules.append((re.compile(r"'''[\s\S]*?'''"), string_format))
        self._highlighting_rules.append((re.compile(r'".*?"'), string_format))
        self._highlighting_rules.append((re.compile(r"'.*?'"), string_format))

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))
        self._highlighting_rules.append((re.compile(r'\b[0-9]+(\.[0-9]+)?\b'), number_format))

        # Function definitions
        func_format = QTextCharFormat()
        func_format.setForeground(QColor("#4EC9B0"))
        self._highlighting_rules.append((re.compile(r'\bdef\b\s+(\w+)'), func_format))

        # Class definitions
        class_format = QTextCharFormat()
        class_format.setForeground(QColor("#4EC9B0"))
        self._highlighting_rules.append((re.compile(r'\bclass\b\s+(\w+)'), class_format))

        # Decorators
        decorator_format = QTextCharFormat()
        decorator_format.setForeground(QColor("#DCDCAA"))
        self._highlighting_rules.append((re.compile(r'@\w+'), decorator_format))

        # Booleans and None
        bool_format = QTextCharFormat()
        bool_format.setForeground(QColor("#F44747"))
        for word in ['True', 'False', 'None']:
            pattern = re.compile(r'\b' + word + r'\b')
            self._highlighting_rules.append((pattern, bool_format))

        # PyFirmata2 keywords
        pyfirmata_format = QTextCharFormat()
        pyfirmata_format.setForeground(QColor("#FF8800"))
        pyfirmata_words = [
            'Board', 'Arduino', 'SERVO', 'PWM', 'INPUT', 'OUTPUT',
            'digital', 'analog', 'Pin', 'servo_write', 'analog_read', 'write', 'read'
        ]
        for word in pyfirmata_words:
            pattern = re.compile(r'\b' + word + r'\b')
            self._highlighting_rules.append((pattern, pyfirmata_format))

    def highlightBlock(self, text: str):
        for pattern, fmt in self._highlighting_rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)

# -----------------------------
# Main Window
# -----------------------------
class VSCodeClone(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyCode - Python IDE")
        self.resize(1200, 800)
        self.explorer_width = 200

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.create_activity_bar()
        self.create_side_bar()
        self.create_editor()
        self.main_splitter.addWidget(self.side_bar)
        self.main_splitter.addWidget(self.editor)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([self.explorer_width, self.width() - self.explorer_width])
        self.setCentralWidget(self.main_splitter)
        self.create_menus()
        self.apply_styles()
        self.statusBar().showMessage("Pronto")

    # Activity Bar
    def create_activity_bar(self):
        self.activity_bar = QToolBar("Activity Bar")
        self.activity_bar.setMovable(False)
        self.activity_bar.setIconSize(QSize(32, 32))
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.activity_bar)
        self.files_action = QAction(QIcon.fromTheme("folder"), "Explorer", self)
        self.files_action.setCheckable(True)
        self.files_action.setChecked(True)
        self.files_action.triggered.connect(self.toggle_explorer)
        self.activity_bar.addAction(self.files_action)

    def toggle_explorer(self, checked):
        if checked:
            self.side_bar.show()
            self.main_splitter.setSizes([self.explorer_width, self.width() - self.explorer_width])
        else:
            self.side_bar.hide()

    # Sidebar
    def create_side_bar(self):
        self.model = QFileSystemModel()
        current_path = os.path.dirname(os.path.abspath(__file__))
        self.model.setRootPath(current_path)
        self.side_bar = QTreeView()
        self.side_bar.setModel(self.model)
        self.side_bar.setRootIndex(self.model.index(current_path))
        for i in range(1, 4):
            self.side_bar.setColumnHidden(i, True)
        self.side_bar.setHeaderHidden(True)
        self.side_bar.setMinimumWidth(self.explorer_width)
        self.side_bar.doubleClicked.connect(self.tree_open_file)

    # Editor
    def create_editor(self):
        self.editor = CodeEditor()
        self.editor.setPlaceholderText("Escreve o teu código aqui...")
        self.highlighter = PythonHighlighter(self.editor.document())

    # Menus
    def create_menus(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&Ficheiro")
        file_actions = [
            ("&Novo", "Ctrl+N", self.new_file),
            ("&Abrir", "Ctrl+O", self.open_file),
            ("&Guardar", "Ctrl+S", self.save_file),
            ("&Guardar Como...", None, self.save_file_as),
            (None, None, None),
            ("&Fechar", "Ctrl+W", self.close_file),
            ("&Sair", "Alt+F4", self.close)
        ]
        for text, shortcut, slot in file_actions:
            if text:
                action = QAction(text, self)
                if shortcut:
                    action.setShortcut(shortcut)
                action.triggered.connect(slot)
                file_menu.addAction(action)
            else:
                file_menu.addSeparator()

        edit_menu = menubar.addMenu("&Editar")
        edit_actions = [
            ("&Desfazer", "Ctrl+Z", self.editor.undo),
            ("&Refazer", "Ctrl+Y", self.editor.redo),
            (None, None, None),
            ("&Recortar", "Ctrl+X", self.editor.cut),
            ("&Copiar", "Ctrl+C", self.editor.copy),
            ("&Colar", "Ctrl+V", self.editor.paste),
            (None, None, None),
            ("Selecionar &Tudo", "Ctrl+A", self.editor.selectAll),
        ]
        for text, shortcut, slot in edit_actions:
            if text:
                action = QAction(text, self)
                if shortcut:
                    action.setShortcut(shortcut)
                action.triggered.connect(slot)
                edit_menu.addAction(action)
            else:
                edit_menu.addSeparator()

    # File operations
    def new_file(self):
        self.editor.clear()
        self.current_file = None
        self.statusBar().showMessage("Novo ficheiro.")

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir Ficheiro", "", "Python (*.py);;Todos (*)")
        if path:
            self.load_file(path)

    def save_file(self):
        if hasattr(self, "current_file") and self.current_file:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            self.statusBar().showMessage(f"Guardado: {self.current_file}")
        else:
            self.save_file_as()

    def save_file_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar Como", "", "Python (*.py);;Todos (*)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            self.current_file = path
            self.statusBar().showMessage(f"Guardado: {path}")

    def close_file(self):
        self.editor.clear()
        self.current_file = None
        self.statusBar().showMessage("Ficheiro fechado.")

    def tree_open_file(self, index):
        path = self.model.filePath(index)
        if not self.model.isDir(index):
            self.load_file(path)

    def load_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.editor.setPlainText(f.read())
            self.current_file = path
            self.statusBar().showMessage(f"Aberto: {path}")
        except Exception as e:
            self.statusBar().showMessage(f"Erro ao abrir: {e}")

    # Styles
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QMenuBar { background-color: #3c3c3c; color: #cccccc; }
            QMenuBar::item:selected { background-color: #505050; }
            QToolBar { background-color: #333333; border: none; spacing: 10px; padding: 5px; }
            QTreeView { background-color: #252526; color: #cccccc; border: none; }
            QPlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; font-family: 'Consolas', monospace; font-size: 15px; selection-background-color: #264f78; }
            QStatusBar { background-color: #007acc; color: white; }
        """)

# Run
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = VSCodeClone()
    window.show()
    sys.exit(app.exec())
