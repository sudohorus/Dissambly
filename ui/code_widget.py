from PyQt6.QtWidgets import QPlainTextEdit
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

class CodeWidget(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Consolas", 11))
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #2B2B2B;
                color: #FFFFFF;
                border: 1px solid #3C3C3C;
                border-radius: 5px;
            }
        """)
        self.connections = []
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setViewportMargins(50, 0, 50, 0)
        
    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoomIn(2)
            else:
                self.zoomOut(2)
        else:
            super().wheelEvent(event)