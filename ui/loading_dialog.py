from PyQt6.QtWidgets import QProgressDialog
from PyQt6.QtCore import Qt

class LoadingDialog(QProgressDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dissambly")
        self.setLabelText("Decompiling file...")
        self.setCancelButton(None)
        self.setRange(0, 100)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setStyleSheet("""
            QProgressDialog {
                background-color: #2B2B2B;
                color: white;
            }
            QProgressBar {
                border: 1px solid #4ECDC4;
                border-radius: 3px;
                text-align: center;
                background-color: #2B2B2B;
            }
            QProgressBar::chunk {
                background-color: #4ECDC4;
            }
        """)