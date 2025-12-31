import sys
import subprocess
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTextEdit, 
                             QPushButton, QVBoxLayout, QHBoxLayout, QWidget, 
                             QSplitter, QPlainTextEdit, QStatusBar, QFileDialog, QLineEdit)
from PyQt6.QtGui import (QFont, QSyntaxHighlighter, QTextCharFormat, QColor, 
                         QTextCursor, QAction)
from PyQt6.QtCore import Qt, QRegularExpression, QThread, pyqtSignal

# --- IMPORTAÇÃO DA CONFIGURAÇÃO EXTERNA ---
try:
    from config_inicial import inicializar_ambiente_wandi
except ImportError:
    def inicializar_ambiente_wandi(): return None

# --- CORES ---
COLOR_BG = "#0b1622"
COLOR_EDITOR = "#152233"
COLOR_CONSOLE = "#050a0f"
COLOR_ACCENT = "#3498db"
COLOR_TEXT = "#d1dce8"

# --- WORKER DE EXECUÇÃO ---
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
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if self.processo.stdout:
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

# --- HIGHLIGHTER ---
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        kw_format = QTextCharFormat()
        kw_format.setForeground(QColor("#56b6c2"))
        kw_format.setFontWeight(QFont.Weight.Bold)
        keywords = ["def", "class", "if", "else", "elif", "for", "while", "return", 
                    "import", "from", "print", "input", "try", "except", "with", "as"]
        for word in keywords:
            self.rules.append((QRegularExpression(f"\\b{word}\\b"), kw_format))
        
        str_format = QTextCharFormat()
        str_format.setForeground(QColor("#98c379"))
        self.rules.append((QRegularExpression(r"\".*\""), str_format))
        self.rules.append((QRegularExpression(r"'.*'"), str_format))
        
        comm_format = QTextCharFormat()
        comm_format.setForeground(QColor("#5c6370"))
        self.rules.append((QRegularExpression(r"#.*"), comm_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

# --- CONSOLE ---
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
            self.input_enviado.emit(linha)
        super().keyPressEvent(event)

# --- JANELA PRINCIPAL ---
class MeuEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.caminho_wandi = inicializar_ambiente_wandi()
        self.setWindowTitle("Wandi Studio IDE v1.0 - Robotic System")
        self.setGeometry(100, 100, 1200, 800)
        self.caminho_arquivo = None
        self.init_ui()
        self.criar_menus()

    def init_ui(self):
        central_container = QWidget()
        central_container.setStyleSheet(f"background-color: {COLOR_BG};")
        self.setCentralWidget(central_container)
        main_layout = QVBoxLayout(central_container)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- Toolbar ---
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(20, 10, 20, 10)
        self.btn_rodar = self.criar_botao("▶ RUN", self.executar, "#158845")
        self.btn_parar = self.criar_botao("⏹ STOP", self.parar_execucao, "#74362F")
        toolbar.addWidget(self.btn_rodar)
        toolbar.addWidget(self.btn_parar)
        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # --- Editor e Área Inferior ---
        splitter_code = QSplitter(Qt.Orientation.Vertical)
        
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 12))
        self.editor.setAcceptRichText(False)
        self.editor.setStyleSheet(f"background-color: {COLOR_EDITOR}; color: {COLOR_TEXT}; border: none; padding: 10px;")
        self.highlighter = PythonHighlighter(self.editor.document())

        # Container Inferior (Serial Input + Console)
        container_inferior = QWidget()
        layout_inferior = QVBoxLayout(container_inferior)
        layout_inferior.setContentsMargins(0, 0, 0, 0)
        layout_inferior.setSpacing(2)

        # SERIAL INPUT (Para qualquer caractere do teclado)
        self.serial_input = QLineEdit()
        self.serial_input.setPlaceholderText("SERIAL INPUT: Digite aqui caracteres para enviar ao Arduino...")
        self.serial_input.setStyleSheet(f"""
            background-color: {COLOR_CONSOLE}; 
            color: #00ff41; 
            border: 1px solid {COLOR_ACCENT}; 
            padding: 5px; 
            font-family: 'Consolas';
        """)
        self.serial_input.returnPressed.connect(self.enviar_comando_serial)

        self.console = ConsoleInterativo()
        self.console.input_enviado.connect(self.enviar_input_ao_worker)

        layout_inferior.addWidget(self.serial_input)
        layout_inferior.addWidget(self.console)

        splitter_code.addWidget(self.editor)
        splitter_code.addWidget(container_inferior)
        splitter_code.setStretchFactor(0, 3)
        splitter_code.setStretchFactor(1, 1)
        main_layout.addWidget(splitter_code)

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet(f"color: #5c6370; background-color: {COLOR_BG};")
        self.status_bar.showMessage("Pronto")

    def criar_menus(self):
        menubar = self.menuBar()
        menubar.setStyleSheet(f"""
            QMenuBar {{ background-color: {COLOR_BG}; color: {COLOR_TEXT}; border-bottom: 1px solid #1c2b3d; }}
            QMenuBar::item:selected {{ background-color: {COLOR_ACCENT}; color: white; }}
            QMenu {{ background-color: {COLOR_EDITOR}; color: {COLOR_TEXT}; border: 1px solid {COLOR_ACCENT}; }}
            QMenu::item:selected {{ background-color: {COLOR_ACCENT}; }}
        """)

        file_menu = menubar.addMenu("&File")
        file_actions = [
            ("Novo", "Ctrl+N", self.novo_arquivo),
            ("Abrir...", "Ctrl+O", self.abrir_arquivo),
            ("Salvar", "Ctrl+S", self.salvar_arquivo),
            (None, None, None),
            ("Sair", "Alt+F4", self.close)
        ]
        for nome, atalho, func in file_actions:
            if nome is None: file_menu.addSeparator()
            else:
                action = QAction(nome, self)
                if atalho: action.setShortcut(atalho)
                action.triggered.connect(func)
                file_menu.addAction(action)

        edit_menu = menubar.addMenu("&Edit")
        edit_actions = [
            ("Desfazer", "Ctrl+Z", self.editor.undo),
            ("Refazer", "Ctrl+Y", self.editor.redo),
            (None, None, None),
            ("Recortar", "Ctrl+X", self.editor.cut),
            ("Copiar", "Ctrl+C", self.editor.copy),
            ("Colar", "Ctrl+V", self.editor.paste),
            (None, None, None),
            ("Selecionar Tudo", "Ctrl+A", self.editor.selectAll)
        ]
        for nome, atalho, func in edit_actions:
            if nome is None: edit_menu.addSeparator()
            else:
                action = QAction(nome, self)
                if atalho: action.setShortcut(atalho)
                action.triggered.connect(func)
                edit_menu.addAction(action)

    def novo_arquivo(self):
        self.editor.clear()
        self.caminho_arquivo = None
        self.status_bar.showMessage("Novo arquivo")

    def abrir_arquivo(self):
        caminho, _ = QFileDialog.getOpenFileName(self, "Abrir Arquivo", "", "Python (*.py);;Todos os Arquivos (*)")
        if caminho:
            with open(caminho, 'r', encoding='utf-8') as f:
                self.editor.setPlainText(f.read())
            self.caminho_arquivo = caminho
            self.status_bar.showMessage(f"Aberto: {caminho}")

    def salvar_arquivo(self):
        if not self.caminho_arquivo:
            caminho, _ = QFileDialog.getSaveFileName(self, "Salvar Arquivo", "", "Python (*.py);;Todos os Arquivos (*)")
            if caminho: self.caminho_arquivo = caminho
            else: return
        with open(self.caminho_arquivo, 'w', encoding='utf-8') as f:
            f.write(self.editor.toPlainText())
        self.status_bar.showMessage(f"Salvo: {self.caminho_arquivo}")

    def criar_botao(self, texto, func, cor):
        btn = QPushButton(texto)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ background-color: {cor}; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px; border: none; }}
            QPushButton:hover {{ background-color: white; color: {cor}; }}
        """)
        btn.clicked.connect(func)
        return btn

    def executar(self):
        codigo = self.editor.toPlainText()
        if not codigo.strip(): return
        self.console.clear()
        self.status_bar.showMessage("Executando...")
        self.worker = ExecutorWorker(codigo)
        self.worker.line_received.connect(self.adicionar_ao_console)
        self.worker.finished.connect(lambda: self.status_bar.showMessage("Finalizado.", 5000))
        self.worker.start()

    def adicionar_ao_console(self, texto):
        self.console.insertPlainText(texto)
        self.console.moveCursor(QTextCursor.MoveOperation.End)

    def parar_execucao(self):
        if hasattr(self, 'worker'):
            self.worker.stop()
            self.status_bar.showMessage("Interrompido.")

    def enviar_input_ao_worker(self, texto):
        if hasattr(self, 'worker'):
            self.worker.enviar_input(texto)

    def enviar_comando_serial(self):
        comando = self.serial_input.text()
        if comando:
            self.enviar_input_ao_worker(comando)
            self.adicionar_ao_console(f"> {comando}\n")
            self.serial_input.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    janela = MeuEditor()
    janela.show()
    sys.exit(app.exec())