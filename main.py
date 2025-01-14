import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                         QWidget, QLabel, QFileDialog, QProgressDialog,
                         QPlainTextEdit, QScrollBar, QMenuBar, QMenu, QMessageBox,
                         QFontDialog, QStatusBar)
from PyQt6.QtGui import (QFont, QSyntaxHighlighter, QTextCharFormat, QColor,
                      QPainter, QPen, QPainterPath, QAction, QKeySequence)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QRect, QPoint, QSettings
import subprocess
import re
import math

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

class DecompileThread(QThread):
    finished = pyqtSignal(str, list)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            self.progress.emit(20)
            
            process = subprocess.Popen(
                ['objdump', '-d', '-M', 'intel', self.file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.progress.emit(40)
            output, error = process.communicate()
            
            self.progress.emit(60)
            
            if process.returncode != 0:
                process = subprocess.Popen(
                    ['dumpbin', '/DISASM', self.file_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                output, error = process.communicate()
            
            self.progress.emit(80)
            
            if process.returncode == 0:
                processed_output, connections = self.process_output(output)
                self.progress.emit(100)
                self.finished.emit(processed_output, connections)
            else:
                raise Exception(f"Erro na decompilação: {error}")

        except FileNotFoundError:
            self.error.emit(
                "Error: You need to have binutils (objdump) or dumpbin installed.\n\n"
                "For Linux:\n"
                "sudo apt-get install binutils\n\n"
                "For Windows:\n"
                "1. Install MinGW or\n"
                "2. Use the tools from Visual Studio Build Tools (dumpbin)"
            )
        except Exception as e:
            self.error.emit(str(e))

    def process_output(self, output):
        lines = output.split('\n')
        processed_lines = []
        connections = []
        address_to_line = {}
        current_line = 0
        
        for line in lines:
            if line.strip():
                addr_match = re.match(r'^\s*([0-9a-fA-F]+):', line)
                if addr_match:
                    addr = int(addr_match.group(1), 16)
                    address_to_line[addr] = current_line
                processed_lines.append(line)
                current_line += 1
        
        current_line = 0
        for line in processed_lines:
            jump_match = re.search(r'\b(jmp|je|jne|jg|jl|jge|jle|ja|jb|jae|jbe|call|loop)\s+([0-9a-fA-F]+)', line)
            if jump_match:
                target_addr = int(jump_match.group(2), 16)
                if target_addr in address_to_line:
                    connections.append((current_line, address_to_line[target_addr]))
            current_line += 1
        
        return '\n'.join(processed_lines), connections

class DissamblyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.base_title = "Dissambly"
        self.setWindowTitle(self.base_title)
        self.setMinimumSize(900, 700)
        self.current_file = None
        self.settings = QSettings('Dissambly', 'DissamblyApp')
        self.setup_ui()
        self.setup_menubar()
        self.load_settings()
        
        self.decompile_thread = None
        self.loading_dialog = None
        
    def setup_ui(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        self.file_label = QLabel()
        self.file_label.setStyleSheet("color: #666; font-size: 12px;")
        self.file_label.setWordWrap(True)
        self.main_layout.addWidget(self.file_label)
        
        self.text_edit = CodeWidget()
        self.highlighter = AssemblyHighlighter(self.text_edit.document())
        self.main_layout.addWidget(self.text_edit)
        

    def setup_menubar(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu('&File')
        
        open_action = QAction('&Open...', self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.select_file)
        file_menu.addAction(open_action)
        
        save_action = QAction('&Save As...', self)
        save_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_action.triggered.connect(self.save_assembly)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('&Exit', self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        edit_menu = menubar.addMenu('&Edit')
        
        font_action = QAction('&Change Font...', self)
        font_action.triggered.connect(self.change_font)
        edit_menu.addAction(font_action)
        
        view_menu = menubar.addMenu('&View')
        
        zoom_in_action = QAction('Zoom &In', self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(lambda: self.text_edit.zoomIn(2))
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction('Zoom &Out', self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(lambda: self.text_edit.zoomOut(2))
        view_menu.addAction(zoom_out_action)
        
        help_menu = menubar.addMenu('&Help')
        
        about_action = QAction('&About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def change_font(self):
        current_font = self.text_edit.font()
        font, ok = QFontDialog.getFont(current_font, self)
        if ok:
            self.text_edit.setFont(font)
            self.settings.setValue('font', font.toString())
            
    def show_about(self):
        QMessageBox.about(self, 'About Dissambly',
            'Dissambly is a tool for decompiling executable files into assembly code.\n\n'
            'Version: 1.0\n'
            'Author: sudohorus\n'
            'License: MIT')
            
    def load_settings(self):
        geometry = self.settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)
            
        font_str = self.settings.value('font')
        if font_str:
            font = QFont()
            font.fromString(font_str)
            self.text_edit.setFont(font)
            
    def closeEvent(self, event):
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('font', self.text_edit.font().toString())
        event.accept()
        
    def select_file(self):
        last_dir = self.settings.value('last_directory', '')
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select .exe file",
            last_dir,
            ".exe Files (*.exe)"
        )
        
        if file_path:
            self.settings.setValue('last_directory', os.path.dirname(file_path))
            self.current_file = file_path
            file_name = os.path.basename(file_path)
            self.setWindowTitle(f"{self.base_title} - {file_name}")
            self.file_label.setText(file_path)
            self.status_bar.showMessage(f"Loading {file_name}...")
            self.start_decompile(file_path)

    def start_decompile(self, file_path):
        self.loading_dialog = LoadingDialog(self)
        self.loading_dialog.show()
        
        self.decompile_thread = DecompileThread(file_path)
        self.decompile_thread.finished.connect(self.on_decompile_finished)
        self.decompile_thread.error.connect(self.on_decompile_error)
        self.decompile_thread.progress.connect(self.loading_dialog.setValue)
        self.decompile_thread.start()

    def on_decompile_finished(self, output, connections):
        self.text_edit.clear()
        chunk_size = 1000
        
        for i in range(0, len(output), chunk_size):
            chunk = output[i:i + chunk_size]
            QTimer.singleShot(0, lambda text=chunk: self.text_edit.insertPlainText(text))
        
        self.text_edit.connections = connections
        
        if self.loading_dialog:
            self.loading_dialog.close()
            
        self.status_bar.showMessage("Decompilation completed", 5000)

    def on_decompile_error(self, error_msg):
        self.text_edit.setText(error_msg)
        if self.loading_dialog:
            self.loading_dialog.close()
        self.setWindowTitle(self.base_title)
        self.status_bar.showMessage("Error during decompilation", 5000)
    
    def save_assembly(self):
        if not self.text_edit.toPlainText().strip():
            return
            
        suggested_name = ""
        if self.current_file:
            base_name = os.path.splitext(os.path.basename(self.current_file))[0]
            suggested_name = f"{base_name}.asm"
            
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Assembly File",
            suggested_name,
            "Assembly File (*.asm)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(self.text_edit.toPlainText())
                self.status_bar.showMessage(f"File saved successfully: {file_path}", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")
                self.status_bar.showMessage("Error saving file", 5000)

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