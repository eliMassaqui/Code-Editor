from PyQt6.QtWidgets import QSplashScreen
from PyQt6.QtGui import QFont, QColor, QLinearGradient, QPainter, QBrush, QPixmap
from PyQt6.QtCore import Qt

class WandiSplash(QSplashScreen):
    def __init__(self):
        super().__init__()
        self.setFixedSize(1280, 720)
        pixmap = QPixmap(self.size())
        painter = QPainter(pixmap)
        
        # Fundo em Gradiente
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor("#33B4FF"))
        gradient.setColorAt(1.0, QColor("#132E99"))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, self.width(), self.height())
        
        # Texto Principal
        painter.setPen(QColor("#ffffff"))
        font = QFont("Segoe UI", 40, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Wandi Studio")
        
        # Subtexto de Carregamento
        painter.setFont(QFont("Segoe UI", 10))
        painter.setPen(QColor("#3498db"))
        painter.drawText(self.rect().adjusted(0, 100, 0, 0), Qt.AlignmentFlag.AlignCenter, "Inicializando Sistema...")
        
        painter.end()
        self.setPixmap(pixmap)