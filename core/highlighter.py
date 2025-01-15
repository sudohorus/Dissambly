import re
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

class AssemblyHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._formats = {}
        
        self.register_format = self.create_format("#FF6B6B")
        self.instruction_format = self.create_format("#4ECDC4")
        self.jump_format = self.create_format("#FFD93D")
        self.number_format = self.create_format("#95A5A6")
        self.address_format = self.create_format("#F7D794")
        self.comment_format = self.create_format("#95A5A6", italic=True)
        
        self.patterns = [
            (re.compile(r'\b(eax|ebx|ecx|edx|esi|edi|esp|ebp|ax|bx|cx|dx|si|di|sp|bp|al|bl|cl|dl)\b'), 
             self.register_format),
            (re.compile(r'\b(mov|push|pop|call|ret|add|sub|mul|div|and|or|xor|inc|dec)\b'),
             self.instruction_format),
            (re.compile(r'\b(jmp|je|jne|jg|jl|jge|jle|ja|jb|jae|jbe|loop)\b'),
             self.jump_format),
            (re.compile(r'\b(0x[0-9a-fA-F]+|\d+)\b'),
             self.number_format),
            (re.compile(r'^\s*[0-9a-fA-F]+:'),
             self.address_format),
            (re.compile(r';.*$'),
             self.comment_format)
        ]

    def create_format(self, color, bold=False, italic=False):
        key = f"{color}-{bold}-{italic}"
        if key not in self._formats:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(QFont.Weight.Bold)
            if italic:
                fmt.setFontItalic(True)
            self._formats[key] = fmt
        return self._formats[key]

    def highlightBlock(self, text):
        for pattern, format in self.patterns:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), format)