import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import DissamblyWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    app.setStyleSheet("""
        QMenuBar {
            background-color: #2B2B2B;
            color: white;
        }
        QMenuBar::item:selected {
            background-color: #3C3C3C;
        }
        QMenu {
            background-color: #2B2B2B;
            color: white;
            border: 1px solid #3C3C3C;
        }
        QMenu::item:selected {
            background-color: #4ECDC4;
        }
        QStatusBar {
            background-color: #2B2B2B;
            color: white;
        }
        QMessageBox {
            background-color: #2B2B2B;
            color: white;
        }
        QMessageBox QPushButton {
            background-color: #4ECDC4;
            color: white;
            border: none;
            padding: 5px 15px;
            border-radius: 3px;
        }
        QMessageBox QPushButton:hover {
            background-color: #45B7AF;
        }
        QFontDialog {
            background-color: #2B2B2B;
            color: white;
        }
    """)
    
    window = DissamblyWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()