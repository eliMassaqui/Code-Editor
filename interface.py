import sys
import subprocess
import os
import shutil
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTextEdit, 
                             QPushButton, QVBoxLayout, QHBoxLayout, QWidget, 
                             QSplitter, QPlainTextEdit, QStatusBar, QFileDialog, QLineEdit, QTabWidget, QFrame, QLabel, QComboBox)
from PyQt6.QtGui import (QFont, QSyntaxHighlighter, QTextCharFormat, QColor, 
                         QTextCursor, QAction, QIcon)
from PyQt6.QtCore import Qt, QRegularExpression, QThread, pyqtSignal, QSize, QTimer

from arduino_engine import ArduinoEngineOverlay 
from firmata_manager import FirmataManager # Importado para o gerenciamento

from firmata_ui import FirmataCardOverlay

# --- IMPORTAÇÃO DA CONFIGURAÇÃO EXTERNA ---
try:
    from config_inicial import inicializar_ambiente_wandi
except ImportError:
    def inicializar_ambiente_wandi(): return None

# --- CONFIGURAÇÕES ARDUINO ---
BOARD = "arduino:avr:uno"

class PortScannerThread(QThread):
    ports_signal = pyqtSignal(list)
    def run(self):
        try:
            fm = FirmataManager() # Usa o caminho do CLI definido no manager
            flags = 0x08000000 if os.name == 'nt' else 0
            output = subprocess.run([fm.cli_path, "board", "list"], capture_output=True, text=True, creationflags=flags)
            lines = output.stdout.splitlines()
            ports = [line.split()[0] for line in lines if "COM" in line or "/dev/tty" in line]
            self.ports_signal.emit(ports)
        except: self.ports_signal.emit([])

# --- CORES ---
COLOR_BG = "#0b1622"
COLOR_EDITOR = "#152233"
COLOR_CONSOLE = "#050a0f"
COLOR_ACCENT = "#3498db"
COLOR_TEXT = "#d1dce8"
COLOR_DEEP_BLUE = "#0d1b2a"

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
            creationflags=0x08000000 if os.name == 'nt' else 0
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

# --- JANELA PRINCIPAL ---
class MeuEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.caminho_wandi = inicializar_ambiente_wandi()
        self.setWindowTitle("Wandi Studio IDE v1.0 - Robotic System")
        self.caminho_arquivo = None
        
        # INICIALIZA O GERENCIADOR
        self.firmata = FirmataManager(BOARD)
        self.firmata.log_received.connect(self.adicionar_ao_output)

        self.init_ui()
        # Após self.init_ui()
        self.ultimo_tipo_compilado = "Standard" # Valor padrão
        self.card_instalar = FirmataCardOverlay(self, cores={
            "bg": COLOR_DEEP_BLUE,
            "accent": COLOR_ACCENT,
            "text": "#00ffdd"
        })
        self.card_instalar.firmata_selected.connect(self.processar_compilacao_firmata)
        self.criar_menus()

        self.engine_overlay = ArduinoEngineOverlay(self)
        self.engine_overlay.iniciar()

        self.scanner_thread = PortScannerThread()
        self.scanner_thread.ports_signal.connect(self.atualizar_lista_portas)
        self.timer_portas = QTimer()
        self.timer_portas.timeout.connect(self.scanner_thread.start)
        self.timer_portas.start(3000)
        self.scanner_thread.start()

    def atualizar_lista_portas(self, ports):
        current = self.port_dropdown.currentText()
        existing = [self.port_dropdown.itemText(i) for i in range(self.port_dropdown.count())]
        if set(ports) != set(existing):
            self.port_dropdown.clear()
            self.port_dropdown.addItems(ports)
            if current in ports:
                self.port_dropdown.setCurrentText(current)

    def executar_compilacao_firmata(self):
        """Abre o card flutuante para escolha do tipo."""
        self.card_instalar.mostrar()

    def processar_compilacao_firmata(self, tipo_escolhido):
        """Chamado após o card (teclado ou clique)."""
        self.ultimo_tipo_compilado = tipo_escolhido # Salva para o upload posterior
        self.tabs_inferiores.setCurrentIndex(0)
        self.firmata.compile_firmata(tipo_escolhido)

    def executar_upload_firmata(self):
        """Faz o upload do que foi selecionado na última compilação."""
        porta = self.port_dropdown.currentText()
        if not porta:
            self.adicionar_ao_output("\n❌ Erro: Selecione uma porta USB!\n")
            return
        
        self.parar_execucao()
        self.tabs_inferiores.setCurrentIndex(0)
        # Usa o tipo que foi escolhido no card de compilação
        self.firmata.upload_firmata(porta, self.ultimo_tipo_compilado)


    def limpar_output_sistema(self):
        self.console_output.clear()
        self.status_bar.showMessage("Output do sistema limpo.")

    def limpar_serial_log(self):
        self.serial_log.clear()
        self.status_bar.showMessage("Log Serial limpo.")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'engine_overlay'):
            self.engine_overlay.posicionar_no_canto()
        # ... seu código de overlay ...
        if hasattr(self, 'card_instalar') and self.card_instalar.isVisible():
            self.card_instalar.setGeometry(self.rect())

    def init_ui(self):
        central_container = QWidget()
        central_container.setStyleSheet(f"background-color: {COLOR_BG};")
        self.setCentralWidget(central_container)
        main_layout = QVBoxLayout(central_container)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.container_toolbar = QWidget()
        COR_BARRA = "#5645d6" 
        self.container_toolbar.setStyleSheet(f"background-color: {COR_BARRA}; border-bottom: 1px #5645d6;")
        toolbar_layout = QHBoxLayout(self.container_toolbar)
        toolbar_layout.setContentsMargins(20, 10, 20, 10)

        self.btn_rodar = self.criar_botao("run.png", self.executar)
        self.btn_parar = self.criar_botao("stop.png", self.parar_execucao)
        toolbar_layout.addWidget(self.btn_rodar)
        toolbar_layout.addWidget(self.btn_parar)

        div = QFrame(); div.setFrameShape(QFrame.Shape.VLine)
        div.setStyleSheet("background-color: rgba(255,255,255,0.2); margin: 0 10px;")
        toolbar_layout.addWidget(div)

        self.btn_compilar_f = self.criar_botao("compilar.png", self.executar_compilacao_firmata)
        self.btn_upload_f = self.criar_botao("upload.png", self.executar_upload_firmata)
        toolbar_layout.addWidget(self.btn_compilar_f)
        toolbar_layout.addWidget(self.btn_upload_f)

        toolbar_layout.addWidget(QLabel(" Porta: "))
        self.port_dropdown = QComboBox()
        self.port_dropdown.setMinimumWidth(120)
        self.port_dropdown.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLOR_DEEP_BLUE};
                color: #00ffdd;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                padding: 2px 10px;
            }}
            QComboBox:focus, QComboBox:on {{
                border: 1px solid white;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {COLOR_DEEP_BLUE};
                color: #00ffdd;
                selection-background-color: {COLOR_ACCENT};
                border: 1px solid white;
            }}
        """)
        toolbar_layout.addWidget(self.port_dropdown)

        toolbar_layout.addStretch()
        main_layout.addWidget(self.container_toolbar)

        splitter_code = QSplitter(Qt.Orientation.Vertical)
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 12))
        self.editor.setAcceptRichText(False)
        self.editor.setStyleSheet(f"background-color: {COLOR_EDITOR}; color: {COLOR_TEXT}; border: none; padding: 10px;")
        self.highlighter = PythonHighlighter(self.editor.document())

        self.tabs_inferiores = QTabWidget()
        self.tabs_inferiores.setStyleSheet(f"""
            QTabWidget::pane {{ border-top: 1px solid #1c2b3d; background: {COLOR_CONSOLE}; }}
            QTabBar::tab {{ background: {COLOR_BG}; color: {COLOR_TEXT}; padding: 8px 20px; border: 1px solid #1c2b3d; }}
            QTabBar::tab:selected {{ background: {COLOR_EDITOR}; border-bottom: 2px solid {COLOR_ACCENT}; }}
        """)

        # Aba Output
        self.console_output = QPlainTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.console_output.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.console_output.setFont(QFont("Consolas", 11))
        self.console_output.setStyleSheet(f"background-color: {COLOR_CONSOLE}; color: #82aaff; border: none; padding: 5px;")

        container_output = QWidget(); layout_output_interno = QVBoxLayout(container_output)
        layout_output_interno.setContentsMargins(0, 0, 0, 0); layout_output_interno.setSpacing(0)
        barra_limpeza = QHBoxLayout(); barra_limpeza.addStretch()
        btn_limpar_out = QPushButton("Limpar")
        btn_limpar_out.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_limpar_out.setStyleSheet("QPushButton { background: transparent; color: #5c6370; border: none; padding: 5px; font-size: 10px; } QPushButton:hover { color: white; }")
        btn_limpar_out.clicked.connect(self.limpar_output_sistema)
        barra_limpeza.addWidget(btn_limpar_out)
        layout_output_interno.addLayout(barra_limpeza); layout_output_interno.addWidget(self.console_output)
        self.tabs_inferiores.addTab(container_output, "OUTPUT")

        # Aba Serial Monitor
        container_serial = QWidget(); layout_serial = QVBoxLayout(container_serial)
        layout_serial.setContentsMargins(0, 0, 0, 0); layout_serial.setSpacing(2)
        self.serial_input = QLineEdit()
        self.serial_input.setPlaceholderText("SERIAL INPUT: Digite caracteres para enviar ao Arduino...")
        self.serial_input.setStyleSheet(f"background-color: {COLOR_CONSOLE}; color: #00ff41; border: 1px solid {COLOR_ACCENT}; padding: 5px; font-family: 'Consolas';")
        self.serial_input.returnPressed.connect(self.enviar_comando_serial)
        
        barra_limpeza_serial = QHBoxLayout(); barra_limpeza_serial.addStretch()
        btn_limpar_serial = QPushButton("Limpar Serial")
        btn_limpar_serial.setStyleSheet("QPushButton { background: transparent; color: #5c6370; border: none; padding: 2px 10px; font-size: 10px; }")
        btn_limpar_serial.clicked.connect(self.limpar_serial_log)
        barra_limpeza_serial.addWidget(btn_limpar_serial)

        self.serial_log = QPlainTextEdit(); self.serial_log.setReadOnly(True)
        self.serial_log.setStyleSheet(f"background-color: {COLOR_CONSOLE}; color: #00ff41; border: none; padding: 5px; font-family: 'Consolas';")

        layout_serial.addWidget(self.serial_input); layout_serial.addLayout(barra_limpeza_serial); layout_serial.addWidget(self.serial_log)
        self.tabs_inferiores.addTab(container_serial, "SERIAL MONITOR")

        splitter_code.addWidget(self.editor); splitter_code.addWidget(self.tabs_inferiores)
        splitter_code.setStretchFactor(0, 3); splitter_code.setStretchFactor(1, 1)
        main_layout.addWidget(splitter_code)

        self.status_bar = QStatusBar(); self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet(f"color: #5c6370; background-color: {COLOR_BG};")
        self.status_bar.showMessage("Pronto")

    def criar_menus(self):
        menubar = self.menuBar()
        menubar.setStyleSheet(f"QMenuBar {{ background-color: {COLOR_BG}; color: {COLOR_TEXT}; border-bottom: 1px solid #1c2b3d; }}")
        file_menu = menubar.addMenu("&File")
        file_actions = [("Novo", "Ctrl+N", self.novo_arquivo), ("Abrir...", "Ctrl+O", self.abrir_arquivo), 
                        ("Salvar", "Ctrl+S", self.salvar_arquivo), (None, None, None), ("Sair", "Alt+F4", self.close)]
        for nome, atalho, func in file_actions:
            if nome is None: file_menu.addSeparator()
            else:
                act = QAction(nome, self); 
                if atalho: act.setShortcut(atalho)
                act.triggered.connect(func); file_menu.addAction(act)

        edit_menu = menubar.addMenu("&Edit")
        edit_actions = [("Desfazer", "Ctrl+Z", self.editor.undo), ("Refazer", "Ctrl+Y", self.editor.redo), (None, None, None),
                        ("Recortar", "Ctrl+X", self.editor.cut), ("Copiar", "Ctrl+C", self.editor.copy), ("Colar", "Ctrl+V", self.editor.paste)]
        for nome, atalho, func in edit_actions:
            if nome is None: edit_menu.addSeparator()
            else:
                act = QAction(nome, self); 
                if atalho: act.setShortcut(atalho)
                act.triggered.connect(func); edit_menu.addAction(act)

    def novo_arquivo(self): self.editor.clear(); self.caminho_arquivo = None; self.status_bar.showMessage("Novo arquivo")
    def abrir_arquivo(self):
        caminho, _ = QFileDialog.getOpenFileName(self, "Abrir Arquivo", "", "Python (*.py);;Todos os Arquivos (*)")
        if caminho:
            with open(caminho, 'r', encoding='utf-8') as f: self.editor.setPlainText(f.read())
            self.caminho_arquivo = caminho; self.status_bar.showMessage(f"Aberto: {caminho}")

    def salvar_arquivo(self):
        if not self.caminho_arquivo:
            caminho, _ = QFileDialog.getSaveFileName(self, "Salvar Arquivo", "", "Python (*.py);;Todos os Arquivos (*)")
            if caminho: self.caminho_arquivo = caminho
            else: return
        with open(self.caminho_arquivo, 'w', encoding='utf-8') as f: f.write(self.editor.toPlainText())
        self.status_bar.showMessage(f"Salvo: {self.caminho_arquivo}")

    def criar_botao(self, nome_arquivo, func):
        btn = QPushButton()
        caminho = os.path.join(os.path.dirname(__file__), nome_arquivo)
        btn.setIcon(QIcon(caminho)); btn.setIconSize(QSize(40, 40))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("QPushButton { background-color: rgba(100, 100, 100, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); padding: 3px; border-radius: 5px; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.15); border: 1px solid rgba(255, 255, 255, 0.3); }")
        btn.clicked.connect(func); return btn

    def executar(self):
        codigo = self.editor.toPlainText()
        if not codigo.strip(): return
        self.console_output.clear(); self.status_bar.showMessage("Executando...")
        self.tabs_inferiores.setCurrentIndex(0); self.worker = ExecutorWorker(codigo)
        self.worker.line_received.connect(self.adicionar_ao_output); self.worker.start()

    def adicionar_ao_output(self, texto):
        self.console_output.insertPlainText(texto); self.console_output.moveCursor(QTextCursor.MoveOperation.End)

    def parar_execucao(self):
        if hasattr(self, 'worker'): self.worker.stop(); self.status_bar.showMessage("Interrompido.")

    def enviar_comando_serial(self):
        comando = self.serial_input.text()
        if comando and hasattr(self, 'worker'):
            self.worker.enviar_input(comando); self.serial_log.insertPlainText(f"> {comando}\n"); self.serial_input.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setStyle("Fusion")
    janela = MeuEditor(); janela.showMaximized(); sys.exit(app.exec())