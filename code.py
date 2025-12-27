import sys
import subprocess
import os
import time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTextEdit, 
                             QPushButton, QVBoxLayout, QHBoxLayout, QWidget, 
                             QSplitter, QPlainTextEdit, QFileDialog, QStatusBar,
                             QListWidget, QStackedWidget, QTreeView, QSplashScreen,
                             QTabWidget, QLineEdit, QToolBar) # Adicionado QTabWidget, QLineEdit
from PyQt6.QtGui import (QFont, QSyntaxHighlighter, QTextCharFormat, QColor, 
                         QTextCursor, QIcon, QFileSystemModel, QLinearGradient, QPainter, QBrush, QPixmap, QAction)
from PyQt6.QtCore import Qt, QRegularExpression, QThread, pyqtSignal, QSize, QUrl

# IMPORTANTE: Importação do motor Web
from PyQt6.QtWebEngineWidgets import QWebEngineView

# --- CONFIGURAÇÃO DO TEMA ---
COLOR_BG = "#0b1622"
COLOR_SIDEBAR_ICO = "#08101a"
COLOR_SIDEBAR_PANEL = "#0e1a29"
COLOR_EDITOR = "#152233"
COLOR_CONSOLE = "#050a0f"
COLOR_ACCENT = "#3498db"
COLOR_TEXT = "#d1dce8"
COLOR_TAB_ACTIVE = "#1c2d41"

# --- CLASSE DA SPLASH SCREEN (Mantida igual) ---
class WandiSplash(QSplashScreen):
    def __init__(self):
        super().__init__()
        self.setFixedSize(1280, 720)
        pixmap = QPixmap(self.size())
        painter = QPainter(pixmap)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor("#33B4FF"))
        gradient.setColorAt(1.0, QColor("#132E99"))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, self.width(), self.height())
        painter.setPen(QColor("#ffffff"))
        font = QFont("Segoe UI", 40, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Wandi Code")
        painter.setFont(QFont("Segoe UI", 10))
        painter.setPen(QColor("#3498db"))
        painter.drawText(self.rect().adjusted(0, 100, 0, 0), Qt.AlignmentFlag.AlignCenter, "Carregando WebEngine...")
        painter.end()
        self.setPixmap(pixmap)

# --- WORKER DE EXECUÇÃO (Mantido igual) ---
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

# --- HIGHLIGHTER (Mantido igual) ---
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

# --- CONSOLE (Mantido igual) ---
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

# --- NOVO WIDGET: NAVEGADOR WEB ---
class NavegadorWeb(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Barra de navegação
        nav_bar = QHBoxLayout()
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Digite a URL e pressione Enter (ex: https://google.com)")
        self.url_bar.setStyleSheet(f"background-color: {COLOR_SIDEBAR_PANEL}; color: white; padding: 5px; border: 1px solid #333;")
        self.url_bar.returnPressed.connect(self.carregar_url)
        
        btn_reload = QPushButton("⟳")
        btn_reload.setFixedWidth(30)
        btn_reload.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: white; border: none;")
        btn_reload.clicked.connect(lambda: self.browser.reload())

        nav_bar.addWidget(self.url_bar)
        nav_bar.addWidget(btn_reload)
        
        # O Navegador em si
        self.browser = QWebEngineView()
        self.browser.setStyleSheet("background-color: white;") # Web view geralmente tem fundo branco
        self.browser.urlChanged.connect(lambda url: self.url_bar.setText(url.toString()))
        
        # Carrega Google por padrão
        self.browser.setUrl(QUrl("https://www.google.com"))

        layout.addLayout(nav_bar)
        layout.addWidget(self.browser)

    def carregar_url(self):
        url = self.url_bar.text()
        if not url.startswith("http"):
            url = "https://" + url
        self.browser.setUrl(QUrl(url))

# --- JANELA PRINCIPAL ---
class MeuEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wandi Code IDE v2.0 - Web Edition")
        self.setGeometry(100, 100, 1200, 800)
        self.caminho_arquivo = None
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        main_widget.setStyleSheet(f"background-color: {COLOR_BG};")
        self.setCentralWidget(main_widget)
        
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Barra Lateral (Activity Bar)
        self.activity_bar = QListWidget()
        self.activity_bar.setFixedWidth(50)
        self.activity_bar.setStyleSheet(f"""
            QListWidget {{ background-color: {COLOR_SIDEBAR_ICO}; border: none; outline: none; }}
            QListWidget::item {{ height: 50px; text-align: center; color: #5c6370; }}
            QListWidget::item:selected {{ background-color: {COLOR_SIDEBAR_PANEL}; color: {COLOR_ACCENT}; border-left: 2px solid {COLOR_ACCENT}; }}
        """)
        self.activity_bar.addItem("📁")
        self.activity_bar.addItem("🌐") # Ícone para web (opcional)
        self.activity_bar.currentRowChanged.connect(self.alternar_sidebar)

        # Painel Lateral (Arquivos)
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

        # --- ÁREA CENTRAL COM ABAS ---
        # Aqui criamos o gerenciador de abas
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid #1c2d41; background: {COLOR_BG}; }}
            QTabBar::tab {{ background: {COLOR_BG}; color: {COLOR_TEXT}; padding: 8px 20px; }}
            QTabBar::tab:selected {{ background: {COLOR_TAB_ACTIVE}; border-top: 2px solid {COLOR_ACCENT}; color: white; }}
            QTabBar::tab:hover {{ background: {COLOR_SIDEBAR_PANEL}; }}
        """)

        # ABA 1: EDITOR DE CÓDIGO
        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0,0,0,0)

        # Toolbar do Editor
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(10, 5, 10, 5)
        self.btn_rodar = self.criar_botao("▶ RUN", self.executar, "#158845")
        self.btn_parar = self.criar_botao("⏹ STOP", self.parar_execucao, "#74362F")
        toolbar.addWidget(self.btn_rodar)
        toolbar.addWidget(self.btn_parar)
        toolbar.addStretch()

        # Splitter Editor/Console
        splitter_code = QSplitter(Qt.Orientation.Vertical)
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 12))
        self.editor.setAcceptRichText(False)
        self.editor.setStyleSheet(f"background-color: {COLOR_EDITOR}; color: {COLOR_TEXT}; border: none; padding: 10px;")
        self.highlighter = PythonHighlighter(self.editor.document())

        self.console = ConsoleInterativo()
        self.console.input_enviado.connect(self.enviar_input_ao_worker)

        splitter_code.addWidget(self.editor)
        splitter_code.addWidget(self.console)
        splitter_code.setStretchFactor(0, 3)
        splitter_code.setStretchFactor(1, 1)

        editor_layout.addLayout(toolbar)
        editor_layout.addWidget(splitter_code)

        # ABA 2: NAVEGADOR WEB
        self.navegador_web = NavegadorWeb()

        # Adicionando as abas
        self.tabs.addTab(editor_container, "Python Editor")
        self.tabs.addTab(self.navegador_web, "Navegador Web")

        # Montagem Final do Layout Principal
        main_layout.addWidget(self.activity_bar)
        main_layout.addWidget(self.sidebar_panel)
        main_layout.addWidget(self.tabs) # Central agora é o TabWidget

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet(f"color: #5c6370; background-color: {COLOR_SIDEBAR_ICO};")
        self.status_bar.showMessage("Sistema Pronto")

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
        # Lógica simples: se clicar no ícone 0, mostra arquivos. Se for outro, pode esconder ou mostrar outra coisa
        if row == 0:
            if self.sidebar_panel.isVisible():
                self.sidebar_panel.hide()
            else:
                self.sidebar_panel.show()
                self.sidebar_panel.setCurrentIndex(0)
        elif row == 1:
            # Atalho rápido: clicar no ícone web muda para a aba do navegador
            self.tabs.setCurrentIndex(1) 

    def abrir_clique_duplo(self, index):
        caminho = self.model.filePath(index)
        if not self.model.isDir(index):
            try:
                with open(caminho, 'r', encoding='utf-8') as f:
                    self.editor.setPlainText(f.read())
                self.caminho_arquivo = caminho
                self.status_bar.showMessage(f"Arquivo: {caminho}")
                # Foca na aba de código ao abrir arquivo
                self.tabs.setCurrentIndex(0)
            except Exception as e:
                self.status_bar.showMessage(f"Erro ao abrir: {str(e)}")

    def executar(self):
        codigo = self.editor.toPlainText()
        if not codigo.strip(): return
        
        # Garante que está vendo a aba de código ao rodar
        self.tabs.setCurrentIndex(0)
        self.console.clear()
        self.status_bar.showMessage("Executando script...")
        
        self.worker = ExecutorWorker(codigo)
        self.worker.line_received.connect(self.adicionar_ao_console)
        self.worker.finished.connect(lambda: self.status_bar.showMessage("Execução concluída.", 5000))
        self.worker.start()

    def adicionar_ao_console(self, texto):
        self.console.insertPlainText(texto)
        self.console.moveCursor(QTextCursor.MoveOperation.End)

    def parar_execucao(self):
        if hasattr(self, 'worker'):
            self.worker.stop()
            self.status_bar.showMessage("Processo interrompido.")

    def enviar_input_ao_worker(self, texto):
        if hasattr(self, 'worker'):
            self.worker.enviar_input(texto)

# --- INICIALIZAÇÃO DO APP ---
if __name__ == "__main__":
    # Configuração necessária para WebEngine rodar processos de renderização
    # (às vezes necessário no Windows)
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox"

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    splash = WandiSplash()
    splash.show()
    app.processEvents()

    # Inicializa a janela principal
    janela = MeuEditor()
    
    time.sleep(1.5) 

    janela.show()
    splash.finish(janela)

    sys.exit(app.exec())