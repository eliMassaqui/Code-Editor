from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont

class FirmataCardOverlay(QWidget):
    # Sinal que envia o nome do Firmata escolhido para a janela principal
    firmata_selected = pyqtSignal(str)

    def __init__(self, parent=None, cores=None):
        super().__init__(parent)
        # Cores padrão caso não venham da IDE principal
        self.colors = cores or {
            "bg": "#0d1b2a",
            "accent": "#3498db",
            "text": "#00ffdd"
        }
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.hide()

        # Layout para centralização total
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # O Card Central
        self.card = QFrame()
        self.card.setFixedSize(450, 420)
        self.card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['bg']};
                border: 2px solid {self.colors['accent']};
                border-radius: 20px;
            }}
            QLabel {{ color: white; border: none; }}
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.05);
                color: {self.colors['text']};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 12px;
                text-align: left;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['accent']};
                color: white;
            }}
        """)
        
        layout_interno = QVBoxLayout(self.card)
        layout_interno.setContentsMargins(30, 25, 30, 25)
        
        titulo = QLabel("INSTALADOR FIRMATA")
        titulo.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_interno.addWidget(titulo)

        subtitulo = QLabel("Pressione (1-4) ou clique na opção")
        subtitulo.setStyleSheet("color: #5c6370; margin-bottom: 10px;")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_interno.addWidget(subtitulo)

        # Mapeamento: Tecla -> (Nome para o CLI, Título do Botão, Descrição)
        self.opcoes_map = {
            Qt.Key.Key_1: ("Standard", "1. Standard Firmata", "Controle total de pinos I/O."),
            Qt.Key.Key_2: ("Plus", "2. Firmata Plus", "Suporte a sensores específicos."),
            Qt.Key.Key_3: ("Configurable", "3. Configurable Firmata", "Versão modular e flexível."),
            Qt.Key.Key_4: ("Wifi", "4. Wifi Firmata", "Conexão via rede (ESP/Arduino Wifi).")
        }

        for key, (nome, label, desc) in self.opcoes_map.items():
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, n=nome: self.confirmar_escolha(n))
            
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #82aaff; font-size: 10px; margin-left: 10px; margin-bottom: 5px;")
            
            layout_interno.addWidget(btn)
            layout_interno.addWidget(desc_label)

        self.main_layout.addWidget(self.card)

    def keyPressEvent(self, event):
        if event.key() in self.opcoes_map:
            self.confirmar_escolha(self.opcoes_map[event.key()][0])
        elif event.key() == Qt.Key.Key_Escape:
            self.hide()

    def confirmar_escolha(self, nome):
        self.firmata_selected.emit(nome)
        self.hide()

    def mostrar(self):
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.raise_()
        self.show()
        self.setFocus()