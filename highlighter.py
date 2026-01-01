from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QPainter, QTextCursor
from PyQt6.QtCore import Qt, QRect, QSize, QRegularExpression

# --- 1. CLASSE DO HIGHLIGHTER ---
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []

        # Formatos
        kw_format = QTextCharFormat()
        kw_format.setForeground(QColor("#56b6c2")) # Ciano
        kw_format.setFontWeight(QFont.Weight.Bold)

        name_format = QTextCharFormat()
        name_format.setForeground(QColor("#61afef")) # Azul

        str_format = QTextCharFormat()
        str_format.setForeground(QColor("#98c379")) # Verde

        comm_format = QTextCharFormat()
        comm_format.setForeground(QColor("#5c6370")) # Cinza
        
        num_format = QTextCharFormat()
        num_format.setForeground(QColor("#d19a66")) # Laranja/Bege

        op_format = QTextCharFormat()
        op_format.setForeground(QColor("#c678dd")) # Roxo (para operadores)

        # Regras
        keywords = ["def", "class", "if", "else", "elif", "for", "while", "return", 
                    "import", "from", "print", "input", "try", "except", "with", "as", "self"]
        
        for word in keywords:
            self.rules.append((QRegularExpression(f"\\b{word}\\b"), kw_format))

        # Operadores e Delimitadores
        operators = [r"\(", r"\)", r"\[", r"\]", r"\{", r"\}", r"\+", r"\-", r"\*", r"\/", r"\=", r"\!", r"\<", r"\>"]
        for op in operators:
            self.rules.append((QRegularExpression(op), op_format))

        self.rules.append((QRegularExpression(r"\b[0-9]+\b"), num_format))
        self.rules.append((QRegularExpression(r"(?<=def\s)\w+"), name_format))
        self.rules.append((QRegularExpression(r"(?<=class\s)\w+"), name_format))
        self.rules.append((QRegularExpression(r"\".*\""), str_format))
        self.rules.append((QRegularExpression(r"'.*'"), str_format))
        self.rules.append((QRegularExpression(r"#.*"), comm_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


# --- 2. COMPONENTES DO NÚMERO DE LINHA ---
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.lineNumberAreaPaintEvent(event)


# --- 3. CLASSE DO EDITOR EVOLUÍDA ---
class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        
        self.line_number_area = LineNumberArea(self)
        
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line) # Nova conexão
        
        self.update_line_number_area_width(0)
        self.highlighter = PythonHighlighter(self.document())
        self.highlight_current_line()

    def highlight_current_line(self):
        """Destaca a linha onde o cursor está posicionado."""
        selection = QTextEdit.ExtraSelection()
        line_color = QColor("#1c2b3d") # Azul bem escuro para o destaque
        selection.format.setBackground(line_color)
        selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])

    def line_number_area_width(self):
        digits = 1
        max_value = max(1, self.blockCount())
        while max_value >= 10:
            max_value /= 10
            digits += 1
        return 15 + self.fontMetrics().horizontalAdvance('9') * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#0b1622")) 

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                # Se for a linha atual, pinto o número com cor mais clara
                is_current = self.textCursor().blockNumber() == block_number
                painter.setPen(QColor("#ffffff") if is_current else QColor("#5c6370"))
                
                painter.drawText(0, top, self.line_number_area.width() - 8, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1