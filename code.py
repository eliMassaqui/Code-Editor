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

class ExecutorWorker(QThread):
    line_received = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, codigo):
        super().__init__()
        self.codigo = codigo
        self.processo = None

    def run(self):
        # Executa o Python em modo não bufferizado (-u) para capturar o output em tempo real
        self.processo = subprocess.Popen(
            [sys.executable, "-u", "-c", self.codigo],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        for linha in self.processo.stdout:
            self.line_received.emit(linha)
            
        self.processo.wait()
        self.finished.emit()

    def stop(self):
        if self.processo:
            self.processo.terminate()

    def enviar_input(self, texto):
        if self.processo and self.processo.poll() is None:
            try:
                self.processo.stdin.write(texto + "\n")
                self.processo.stdin.flush()
            except Exception as e:
                self.line_received.emit(f"\nErro de Input: {str(e)}\n")

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        
        # Palavras-chave
        kw_format = QTextCharFormat()
        kw_format.setForeground(QColor("#56b6c2"))
        kw_format.setFontWeight(QFont.Weight.Bold)
        keywords = ["def", "class", "if", "else", "elif", "for", "while", "return", 
                    "import", "from", "print", "input", "try", "except", "with", "as"]
        for word in keywords:
            self.rules.append((QRegularExpression(f"\\b{word}\\b"), kw_format))

        # Strings
        str_format = QTextCharFormat()
        str_format.setForeground(QColor("#98c379"))
        self.rules.append((QRegularExpression(r"\".*\""), str_format))
        self.rules.append((QRegularExpression(r"'.*'"), str_format))

        # Comentários
        comm_format = QTextCharFormat()
        comm_format.setForeground(QColor("#5c6370"))
        self.rules.append((QRegularExpression(r"#.*"), comm_format))

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
        self.setPlaceholderText("Console de saída e entrada...")

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            linha = cursor.selectedText()
            # Envia apenas a última parte (simulando input)
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

        # 1. Activity Bar (Lateral Estreita)
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

        # 2. Sidebar Panel
        self.sidebar_panel = QStackedWidget()
        self.sidebar_panel.setFixedWidth(220)
        self.sidebar_panel.setStyleSheet(f"background-color: {COLOR_SIDEBAR_PANEL}; border-right: 1px solid #1c2d41;")
        
        self.model = QFileSystemModel()
        self.model.setRootPath(os.getcwd())
        
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(os.getcwd()))
        self.tree.setHeaderHidden(True)
        for i in range(1, 4): self.tree.setColumnHidden(i, True)
        self.tree.setStyleSheet(f"QTreeView {{ color: {COLOR_TEXT}; border: none; background: transparent; }} QTreeView::item:hover {{ background: #1c2d41; }}")
        self.tree.doubleClicked.connect(self.abrir_clique_duplo)

        self.sidebar_panel.addWidget(self.tree)
        self.sidebar_panel.addWidget(QWidget()) 

        # 3. Área Central
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(10, 5, 10, 5)
        self.btn_rodar = self.criar_botao("▶ RUN", self.executar, "#2ecc71")
        self.btn_parar = self.criar_botao("⏹ STOP", self.parar_execucao, "#e74c3c")
        toolbar.addWidget(self.btn_rodar)
        toolbar.addWidget(self.btn_parar)
        toolbar.addStretch()

        # Splitter (Editor em cima, Console embaixo)
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 12))
        self.editor.setAcceptRichText(False)
        self.editor.setStyleSheet(f"background-color: {COLOR_EDITOR}; color: {COLOR_TEXT}; border: 1px solid #1c2d41; padding: 10px;")
        self.highlighter = PythonHighlighter(self.editor.document())

        self.console = ConsoleInterativo()
        self.console.input_enviado.connect(self.enviar_input_ao_worker)

        splitter.addWidget(self.editor)
        splitter.addWidget(self.console)
        splitter.setStretchFactor(0, 3) # Editor ocupa mais espaço
        splitter.setStretchFactor(1, 1)

        content_layout.addLayout(toolbar)
        content_layout.addWidget(splitter)

        main_layout.addWidget(self.activity_bar)
        main_layout.addWidget(self.sidebar_panel)
        main_layout.addWidget(content)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet(f"color: #5c6370; background-color: {COLOR_SIDEBAR_ICO};")
        self.status_bar.showMessage("Pronto")

    def criar_botao(self, texto, func, cor):
        btn = QPushButton(texto)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ background-color: {cor}; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px; border: none; }}
            QPushButton:hover {{ opacity: 0.8; }}
        """)
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
            try:
                with open(caminho, 'r', encoding='utf-8') as f:
                    self.editor.setPlainText(f.read())
                self.caminho_arquivo = caminho
                self.status_bar.showMessage(f"Arquivo: {caminho}")
            except Exception as e:
                self.status_bar.showMessage(f"Erro ao abrir: {str(e)}")

    def executar(self):
        codigo = self.editor.toPlainText()
        if not codigo.strip(): return
        
        self.console.clear()
        self.status_bar.showMessage("Executando script...")
        
        self.worker = ExecutorWorker(codigo)
        self.worker.line_received.connect(self.adicionar_ao_console)
        self.worker.finished.connect(lambda: self.status_bar.showMessage("Execução concluída.", 5000))
        self.worker.start()

    def adicionar_ao_console(self, texto):
        self.console.insertPlainText(texto)
        # Scroll automático
        self.console.moveCursor(QTextCursor.MoveOperation.End)

    def parar_execucao(self):
        if hasattr(self, 'worker'):
            self.worker.stop()
            self.status_bar.showMessage("Processo interrompido.")

    def enviar_input_ao_worker(self, texto):
        if hasattr(self, 'worker'):
            self.worker.enviar_input(texto)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # Estilo moderno multiplataforma
    janela = MeuEditor()
    janela.show()
    sys.exit(app.exec())