import sys
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTextEdit, 
                             QPushButton, QVBoxLayout, QWidget, 
                             QSplitter, QPlainTextEdit)
from PyQt6.QtGui import (QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QTextCursor)
from PyQt6.QtCore import Qt, QRegularExpression, QThread, pyqtSignal

# --- Realce de Sintaxe (Focado no Editor) ---
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []

        # Keywords (Rosa)
        kw_format = QTextCharFormat()
        kw_format.setForeground(QColor("#ff79c6"))
        kw_format.setFontWeight(QFont.Weight.Bold)
        keywords = ["def", "class", "if", "else", "elif", "for", "while", "return", "import", "from", "print", "input", "try", "except"]
        for word in keywords:
            self.rules.append((QRegularExpression(f"\\b{word}\\b"), kw_format))

        # Strings (Amarelo)
        str_format = QTextCharFormat()
        str_format.setForeground(QColor("#f1fa8c"))
        self.rules.append((QRegularExpression("\".*\""), str_format))
        self.rules.append((QRegularExpression("'.*'"), str_format))

        # Comentários (Cinza)
        comm_format = QTextCharFormat()
        comm_format.setForeground(QColor("#6272a4"))
        self.rules.append((QRegularExpression("#.*"), comm_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

# --- Console Interativo ---
class ConsoleInterativo(QPlainTextEdit):
    input_enviado = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setFont(QFont("Consolas", 11))
        self.setStyleSheet("background-color: #1e1e1e; color: #50fa7b; border: none; padding: 5px;")

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            linha = cursor.selectedText()
            self.input_enviado.emit(linha)
        super().keyPressEvent(event)

# --- Thread de Execução ---
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

# --- Janela Principal ---
class MeuEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python IDE v1.3 - Syntax & Input")
        self.setGeometry(100, 100, 1000, 700)
        self.init_ui()

    def init_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        splitter = QSplitter(Qt.Orientation.Vertical)

        # EDITOR PRINCIPAL (Onde a cor deve estar)
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 12))
        self.editor.setStyleSheet("background-color: #282a36; color: #f8f8f2; padding: 10px;")
        
        # REATIVANDO O HIGHLIGHTER NO DOCUMENTO DO EDITOR
        self.highlighter = PythonHighlighter(self.editor.document())

        self.console = ConsoleInterativo()
        self.console.input_enviado.connect(self.enviar_input_ao_worker)

        splitter.addWidget(self.editor)
        splitter.addWidget(self.console)
        splitter.setStretchFactor(0, 3)

        self.btn_rodar = QPushButton("▶ Executar")
        self.btn_rodar.setStyleSheet("background-color: #50fa7b; color: #282a36; font-weight: bold; padding: 10px;")
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