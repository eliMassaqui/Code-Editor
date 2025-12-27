import sys
import subprocess
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTextEdit, 
                             QPushButton, QVBoxLayout, QHBoxLayout, QWidget, 
                             QSplitter, QPlainTextEdit, QFileDialog, QStatusBar,
                             QListWidget, QStackedWidget, QTreeView)
from PyQt6.QtGui import (QFont, QSyntaxHighlighter, QTextCharFormat, QColor, 
                         QTextCursor, QIcon, QFileSystemModel)
from PyQt6.QtCore import Qt, QRegularExpression, QThread, pyqtSignal, QSize

# --- CONFIGURAÇÃO DO TEMA ---
COLOR_BG = "#0b1622"
COLOR_SIDEBAR_ICO = "#08101a"
COLOR_SIDEBAR_PANEL = "#0e1a29"
COLOR_EDITOR = "#152233"
COLOR_CONSOLE = "#050a0f"
COLOR_ACCENT = "#3498db"
COLOR_TEXT = "#d1dce8"

# ... (As classes PythonHighlighter, ConsoleInterativo e ExecutorWorker permanecem as mesmas)

class ExecutorWorker(QThread):
    line_received = pyqtSignal(str)
    finished = pyqtSignal()
    def __init__(self, codigo):
        super().__init__()
        self.codigo = codigo
        self.processo = None
    def run(self):
        self.processo = subprocess.Popen([sys.executable, "-u", "-c", self.codigo],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, text=True, bufsize=1)
        for linha in self.processo.stdout: self.line_received.emit(linha)
        self.processo.wait()
        self.finished.emit()
    def stop(self):
        if self.processo: self.processo.terminate()
    def enviar_input(self, texto):
        if self.processo and self.processo.poll() is None:
            self.processo.stdin.write(texto + "\n")
            self.processo.stdin.flush()

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        kw_format = QTextCharFormat()
        kw_format.setForeground(QColor("#56b6c2"))
        kw_format.setFontWeight(QFont.Weight.Bold)
        keywords = ["def", "class", "if", "else", "elif", "for", "while", "return", "import", "from", "print", "input"]
        for word in keywords:
            self.rules.append((QRegularExpression(f"\\b{word}\\b"), kw_format))
        str_format = QTextCharFormat()
        str_format.setForeground(QColor("#98c379"))
        self.rules.append((QRegularExpression("\".*\""), str_format))
        self.rules.append((QRegularExpression("'.*'"), str_format))
        comm_format = QTextCharFormat()
        comm_format.setForeground(QColor("#5c6370"))
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

class MeuEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BlueCode IDE v1.5")
        self.setGeometry(100, 100, 1100, 800)
        self.caminho_arquivo = None
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        main_widget.setStyleSheet(f"background-color: {COLOR_BG};")
        self.setCentralWidget(main_widget)
        
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Barra de Ícones lateral (Activity Bar)
        self.activity_bar = QListWidget()
        self.activity_bar.setFixedWidth(50)
        self.activity_bar.setStyleSheet(f"""
            QListWidget {{ background-color: {COLOR_SIDEBAR_ICO}; border: none; outline: none; }}
            QListWidget::item {{ height: 50px; text-align: center; color: #5c6370; }}
            QListWidget::item:selected {{ background-color: {COLOR_SIDEBAR_PANEL}; color: {COLOR_ACCENT}; border-left: 2px solid {COLOR_ACCENT}; }}
        """)
        self.activity_bar.addItem("📁")
        self.activity_bar.addItem("⚙️")
        self.activity_bar.currentRowChanged.connect(self.alternar_sidebar)

        # 2. Painel da Sidebar (Explorador)
        self.sidebar_panel = QStackedWidget()
        self.sidebar_panel.setFixedWidth(220)
        self.sidebar_panel.setStyleSheet(f"background-color: {COLOR_SIDEBAR_PANEL}; border-right: 1px solid #1c2d41;")
        
        # Árvore de Arquivos
        self.model = QFileSystemModel()
        self.model.setRootPath(os.getcwd())
        
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(os.getcwd()))
        self.tree.setHeaderHidden(True)
        self.tree.setColumnHidden(1, True)
        self.tree.setColumnHidden(2, True)
        self.tree.setColumnHidden(3, True)
        self.tree.setStyleSheet(f"QTreeView {{ color: {COLOR_TEXT}; border: none; background: transparent; }} QTreeView::item:hover {{ background: #1c2d41; }}")
        self.tree.doubleClicked.connect(self.abrir_clique_duplo)

        self.sidebar_panel.addWidget(self.tree)
        self.sidebar_panel.addWidget(QWidget()) # Placeholder Config

        # 3. Área Central (Editor e Console)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        toolbar = QHBoxLayout()
        self.btn_rodar = self.criar_botao("▶ RUN", self.executar, "#2ecc71")
        self.btn_parar = self.criar_botao("⏹ STOP", self.parar_execucao, "#e74c3c")
        toolbar.addWidget(self.btn_rodar)
        toolbar.addWidget(self.btn_parar)
        toolbar.addStretch()

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 12))
        self.editor.setStyleSheet(f"background-color: {COLOR_EDITOR}; color: {COLOR_TEXT}; border: 1px solid #1c2d41; padding: 10px;")
        self.highlighter = PythonHighlighter(self.editor.document())

        self.console = ConsoleInterativo()
        self.console.input_enviado.connect(self.enviar_input_ao_worker)

        splitter.addWidget(self.editor)
        splitter.addWidget(self.console)
        splitter.setStretchFactor(0, 3)

        content_layout.addLayout(toolbar)
        content_layout.addWidget(splitter)

        main_layout.addWidget(self.activity_bar)
        main_layout.addWidget(self.sidebar_panel)
        main_layout.addWidget(content)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet("color: #5c6370;")

    def criar_botao(self, texto, func, cor=COLOR_ACCENT):
        btn = QPushButton(texto)
        btn.setStyleSheet(f"background-color: {cor}; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px; border: none;")
        btn.clicked.connect(func)
        return btn

    def alternar_sidebar(self, row):
        if self.sidebar_panel.isVisible() and self.sidebar_panel.currentIndex() == row:
            self.sidebar_panel.hide()
        else:
            self.sidebar_panel.show()
            self.sidebar_panel.setCurrentIndex(row)

    def abrir_clique_duplo(self, index):
        caminho = self.model.filePath(index)
        if not self.model.isDir(index):
            with open(caminho, 'r', encoding='utf-8') as f:
                self.editor.setPlainText(f.read())
            self.caminho_arquivo = caminho
            self.status_bar.showMessage(f"Arquivo: {caminho}")

    def executar(self):
        self.console.clear()
        self.worker = ExecutorWorker(self.editor.toPlainText())
        self.worker.line_received.connect(self.console.insertPlainText)
        self.worker.start()

    def parar_execucao(self):
        if hasattr(self, 'worker'): self.worker.stop()

    def enviar_input_ao_worker(self, t):
        if hasattr(self, 'worker'): self.worker.enviar_input(t)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    janela = MeuEditor()
    janela.show()
    sys.exit(app.exec())