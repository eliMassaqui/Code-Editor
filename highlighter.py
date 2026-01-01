from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt6.QtCore import QRegularExpression

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []

        # --- Definição de Cores e Estilos ---
        # Keywords (Azul Ciano)
        kw_format = QTextCharFormat()
        kw_format.setForeground(QColor("#56b6c2"))
        kw_format.setFontWeight(QFont.Weight.Bold)

        # Funções e Classes (Destaque para o nome criado)
        name_format = QTextCharFormat()
        name_format.setForeground(QColor("#61afef")) # Azul vibrante

        # Strings (Verde)
        str_format = QTextCharFormat()
        str_format.setForeground(QColor("#98c379"))

        # Comentários (Cinza)
        comm_format = QTextCharFormat()
        comm_format.setForeground(QColor("#5c6370"))
        
        # Números (Dourado/Laranja)
        num_format = QTextCharFormat()
        num_format.setForeground(QColor("#d19a66"))

        # --- Lista de Regras (Priorizando sua lógica original) ---
        
        # 1. Keywords básicas
        keywords = ["def", "class", "if", "else", "elif", "for", "while", "return", 
                    "import", "from", "print", "input", "try", "except", "with", "as", "self"]
        for word in keywords:
            self.rules.append((QRegularExpression(f"\\b{word}\\b"), kw_format))

        # 2. Números
        self.rules.append((QRegularExpression(r"\b[0-9]+\b"), num_format))

        # 3. Nomes de funções (o que vem após o 'def ')
        self.rules.append((QRegularExpression(r"(?<=def\s)\w+"), name_format))
        
        # 4. Nomes de classes (o que vem após o 'class ')
        self.rules.append((QRegularExpression(r"(?<=class\s)\w+"), name_format))

        # 5. Strings e Comentários (No final para não sobrepor outras regras)
        self.rules.append((QRegularExpression(r"\".*\""), str_format))
        self.rules.append((QRegularExpression(r"'.*'"), str_format))
        self.rules.append((QRegularExpression(r"#.*"), comm_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)