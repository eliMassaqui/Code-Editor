from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit, QApplication
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QPainter, QTextCursor
from PyQt6.QtCore import Qt, QRect, QSize, QRegularExpression, QTimer

# --- 1. CLASSE DO HIGHLIGHTER ---
class PythonHighlighter(QSyntaxHighlighter):

    def __init__(self, document):
        super().__init__(document)
        # 1. Primeiro criamos a lista para ela estar pronta
        self.rules = [] 

        # 2. Agora injetamos as regras do Firmata (importando aqui mesmo)
        import firmata_syntax
        self.rules.extend(firmata_syntax.get_firmata_rules())

        # 3. Definição das Cores e Formatos
        fmt_keyword = self.create_format("#c678dd", bold=True)
        fmt_value = self.create_format("#d19a66") # Laranja
        fmt_builtin = self.create_format("#56b6c2", italic=True)
        fmt_function = self.create_format("#61afef")
        fmt_string = self.create_format("#98c379")
        fmt_comment = self.create_format("#5c6370")
        fmt_decorator = self.create_format("#e5c07b")

        # 4. Regras de Sintaxe Padrão (Python)
        keywords = ["and", "as", "assert", "break", "class", "continue", "def", "del", "elif", "else", "except", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try", "while", "with", "yield", "self"]
        for word in keywords:
            self.rules.append((QRegularExpression(f"\\b{word}\\b"), fmt_keyword))
        
        values = ["True", "False", "None"]
        for word in values:
            self.rules.append((QRegularExpression(f"\\b{word}\\b"), fmt_value))
        
        self.rules.append((QRegularExpression(r"\b[0-9]+\.?[0-9]*\b"), fmt_value))

        # ... (segue o restante do seu código)
        
        builtins = ["print", "input", "len", "range", "list", "dict", "int", "str", "float", "bool"]
        for word in builtins: self.rules.append((QRegularExpression(f"\\b{word}\\b"), fmt_builtin))

        self.rules.append((QRegularExpression(r"@[a-zA-Z_]\w*"), fmt_decorator))
        self.rules.append((QRegularExpression(r"\b\w+(?=\()"), fmt_function))
        self.rules.append((QRegularExpression(r"(?<=def\s)\w+"), fmt_function))
        self.rules.append((QRegularExpression(r"\".*\""), fmt_string))
        self.rules.append((QRegularExpression(r"'.*'"), fmt_string))
        self.rules.append((QRegularExpression(r"#.*"), fmt_comment))
        
        self.tri_double = (QRegularExpression(r'"""'), fmt_string)

    def create_format(self, color, bold=False, italic=False):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold: fmt.setFontWeight(QFont.Weight.Bold)
        if italic: fmt.setFontItalic(True)
        return fmt

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
        
        self.setCurrentBlockState(0)
        start_index = 0
        if self.previousBlockState() != 1:
            match = self.tri_double[0].match(text)
            start_index = match.capturedStart()

        while start_index >= 0:
            match = self.tri_double[0].match(text, start_index + 3)
            end_index = match.capturedStart()
            if end_index == -1:
                self.setCurrentBlockState(1)
                comment_len = len(text) - start_index
            else:
                comment_len = end_index - start_index + 3
            self.setFormat(start_index, comment_len, self.tri_double[1])
            start_index = self.tri_double[0].match(text, start_index + comment_len).capturedStart()

# --- 2. ÁREA DOS NÚMEROS DE LINHA ---
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor
    def sizeHint(self): return QSize(self.code_editor.line_number_area_width(), 0)
    def paintEvent(self, event): self.code_editor.lineNumberAreaPaintEvent(event)

# --- 3. CLASSE DO EDITOR ---
class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.line_number_area = LineNumberArea(self)
        
        # Timer para o efeito do cursor (estilo VS Code)
        self.cursor_timer = QTimer(self)
        self.cursor_timer.setSingleShot(True)
        self.cursor_timer.timeout.connect(self.reset_cursor_blink)
        
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        
        self.update_line_number_area_width(0)
        self.highlighter = PythonHighlighter(self.document())
        self.highlight_current_line()

    def reset_cursor_blink(self):
        # Volta ao tempo padrão de piscar (500ms)
        QApplication.setCursorFlashTime(500)

    def keyPressEvent(self, event):
        # Congela o cursor (para de piscar) enquanto houver atividade
        QApplication.setCursorFlashTime(0)
        self.cursor_timer.start(500)

        cursor = self.textCursor()

        # A. BACKSPACE INTELIGENTE
        if event.key() == Qt.Key.Key_Backspace and not cursor.hasSelection():
            pos_in_block = cursor.positionInBlock()
            line_text = cursor.block().text()
            
            if pos_in_block > 0:
                text_before = line_text[:pos_in_block]
                
                # Apagar pares (), [], ""
                if pos_in_block < len(line_text):
                    char_before = text_before[-1]
                    char_after = line_text[pos_in_block]
                    pairs = {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'"}
                    if char_before in pairs and pairs[char_before] == char_after:
                        cursor.beginEditBlock()
                        cursor.deleteChar()
                        cursor.deletePreviousChar()
                        cursor.endEditBlock()
                        return

                # Apagar indentação de 4 espaços
                if text_before.endswith("    ") and not text_before.strip():
                    cursor.beginEditBlock()
                    for _ in range(4): cursor.deletePreviousChar()
                    cursor.endEditBlock()
                    return

        # B. AUTO-FECHAMENTO
        brackets = {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'"}
        if event.text() in brackets:
            opening = event.text()
            closing = brackets[opening]
            cursor.insertText(opening + closing)
            cursor.movePosition(QTextCursor.MoveOperation.Left)
            self.setTextCursor(cursor)
            return

        # C. AUTO-IDENTAÇÃO
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            line_text = cursor.block().text()
            indentation = ""
            for char in line_text:
                if char.isspace(): indentation += char
                else: break
            if line_text.strip().endswith(':'):
                indentation += "    "
            super().keyPressEvent(event)
            self.insertPlainText(indentation)
            return

        super().keyPressEvent(event)

    # --- MÉTODOS DE UI (NÚMEROS E LINHA ATUAL) ---
    def highlight_current_line(self):
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#1c2b3d"))
        selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])

    def line_number_area_width(self):
        digits = 1
        max_val = max(1, self.blockCount())
        while max_val >= 10: max_val /= 10; digits += 1
        return 15 + self.fontMetrics().horizontalAdvance('9') * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy: self.line_number_area.scroll(0, dy)
        else: self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()): self.update_line_number_area_width(0)

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
                is_curr = self.textCursor().blockNumber() == block_number
                painter.setPen(QColor("#ffffff") if is_curr else QColor("#5c6370"))
                painter.drawText(0, top, self.line_number_area.width()-8, self.fontMetrics().height(), Qt.AlignmentFlag.AlignRight, number)
            block = block.next(); top = bottom; bottom = top + round(self.blockBoundingRect(block).height()); block_number += 1