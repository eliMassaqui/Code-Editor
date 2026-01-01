from PyQt6.QtGui import QColor, QTextCharFormat, QFont

# Cores específicas para Hardware (Destaque Neon/Dourado)
COLOR_HARDWARE = "#e5c07b"  # Dourado/Amarelo
COLOR_PORT = "#d19a66"      # Laranja para portas (COM1, /dev/tty)

def get_firmata_rules():
    """Retorna as regras de sintaxe específicas para pyFirmata2"""
    rules = []

    # Formatos
    fmt_hw = QTextCharFormat()
    fmt_hw.setForeground(QColor(COLOR_HARDWARE))
    fmt_hw.setFontWeight(QFont.Weight.Bold)

    fmt_port = QTextCharFormat()
    fmt_port.setForeground(QColor(COLOR_PORT))

    # 1. Termos de Configuração e Modos
    hw_keywords = [
        "Arduino", "util", "pyfirmata2", "STRING_DATA",
        "INPUT", "OUTPUT", "ANALOG", "PWM", "SERVO", "HIGH", "LOW"
    ]
    
    # 2. Métodos de Ação (Escrita e Leitura)
    hw_methods = [
        "get_pin", "write", "read", "enable_reporting", "disable_reporting",
        "digital", "analog", "exit", "iterator", "Iterator"
    ]

    from PyQt6.QtCore import QRegularExpression

    # Adicionando termos à lista de regras
    for word in hw_keywords + hw_methods:
        rules.append((QRegularExpression(f"\\b{word}\\b"), fmt_hw))

    # Regra para capturar Portas COM ou caminhos USB
    rules.append((QRegularExpression(r"'(COM[0-9]+|/dev/tty[a-zA-Z0-9]+)'"), fmt_port))
    rules.append((QRegularExpression(r'"(COM[0-9]+|/dev/tty[a-zA-Z0-9]+)"'), fmt_port))

    return rules