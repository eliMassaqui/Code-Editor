import sys
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTextEdit, 
                             QPushButton, QVBoxLayout, QWidget, 
                             QSplitter, QPlainTextEdit)
from PyQt6.QtGui import (QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QTextCursor)
from PyQt6.QtCore import Qt, QRegularExpression, QThread, pyqtSignal

# --- CORES DO TEMA AZUL ESCURO ---
COLOR_BG = "#0b1622"        # Fundo principal (Azul Profundo)
COLOR_EDITOR = "#152233"    # Fundo do editor (Azul Marinho)
COLOR_CONSOLE = "#050a0f"   # Fundo do console (Quase preto)
COLOR_TEXT = "#d1dce8"      # Texto padrão
COLOR_ACCENT = "#3498db"    # Azul brilhante para botões
COLOR_KEYWORD = "#56b6c2"   # Ciano para palavras-chave
COLOR_STRING = "#98c379"    # Verde suave para strings
COLOR_COMMENT = "#5c6370"   # Cinza para comentários

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []

        # Keywords (Ciano)
        kw_format = QTextCharFormat()
        kw_format.setForeground(QColor(COLOR_KEYWORD))
        kw_format.setFontWeight(QFont.Weight.Bold)
        keywords = ["def", "class", "if", "else", "elif", "for", "while", "return", "import", "from", "print", "input", "try", "except", "with", "as"]
        for word in keywords:
            self.rules.append((QRegularExpression(f"\\b{word}\\b"), kw_format))

        # Strings (Verde)
        str_format = QTextCharFormat()
        str_format.setForeground(QColor(COLOR_STRING))
        self.rules.append((QRegularExpression("\".*\""), str_format))
        self.rules.append((QRegularExpression("'.*'"), str_format))

        # Comentários (Cinza)
        comm_format = QTextCharFormat()
        comm_format.setForeground(QColor(COLOR_COMMENT))
        self.rules.append((QRegularExpression("#.*"), comm_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

class ConsoleInterativo(QPlainTextEdit):
    input_enviado = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setFont(QFont("Consolas", 11))
        self.setStyleSheet(f"background-color: {COLOR_CONSOLE}; color: #82aaff; border: none; padding: 5px;")

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            linha = cursor.selectedText()
            self.input_enviado.emit(linha)
        super().keyPressEvent(event)

class ExecutorWorker(QThread):
    line_received = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, codigo):
        super().__init__()
        self.codigo = codigo
        self.processo = None

    def run(self):
        self.processo = subprocess.Popen(
            [sys.executable, "-u", "-c", self.codigo],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        for linha in self.processo.stdout:
            self.line_received.emit(linha)
        self.processo.wait()
        self.finished.emit()

    def enviar_input(self, texto):
        if self.processo and self.processo.poll() is None:
            self.processo.stdin.write(texto + "\n")
            self.processo.stdin.flush()

class MeuEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Deep Blue Python IDE")
        self.setGeometry(100, 100, 1000, 750)
        self.init_ui()

    def init_ui(self):
        container = QWidget()
        container.setStyleSheet(f"background-color: {COLOR_BG};")
        layout = QVBoxLayout(container)
        
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Editor
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 12))
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLOR_EDITOR};
                color: {COLOR_TEXT};
                border: 1px solid #1c2d41;
                border-radius: 4px;
                padding: 10px;
            }}
        """)
        self.highlighter = PythonHighlighter(self.editor.document())

        # Console
        self.console = ConsoleInterativo()
        self.console.input_enviado.connect(self.enviar_input_ao_worker)

        splitter.addWidget(self.editor)
        splitter.addWidget(self.console)
        splitter.setStretchFactor(0, 3)

        # Botão Rodar Estilizado
        self.btn_rodar = QPushButton("▶ RUN SCRIPT")
        self.btn_rodar.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_ACCENT};
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 4px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #2980b9;
            }}
            QPushButton:pressed {{
                background-color: #1c5980;
            }}
        """)
        self.btn_rodar.clicked.connect(self.executar)

        layout.addWidget(self.btn_rodar)
        layout.addWidget(splitter)
        self.setCentralWidget(container)

    def executar(self):
        self.console.clear()
        self.worker = ExecutorWorker(self.editor.toPlainText())
        self.worker.line_received.connect(lambda t: self.console.insertPlainText(t))
        self.worker.start()

    def enviar_input_ao_worker(self, texto):
        if hasattr(self, 'worker'):
            self.worker.enviar_input(texto)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    janela = MeuEditor()
    janela.show()
    sys.exit(app.exec())