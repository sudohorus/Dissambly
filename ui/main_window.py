import os
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QLabel, 
                           QFileDialog, QMessageBox, QFontDialog, QStatusBar)
from PyQt6.QtGui import QFont, QAction
from PyQt6.QtCore import QTimer, QSettings

from .code_widget import CodeWidget
from .loading_dialog import LoadingDialog
from core.highlighter import AssemblyHighlighter
from core.decompiler import DecompileThread

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
        self.text_edit.setUndoRedoEnabled(True)
        self.highlighter = AssemblyHighlighter(self.text_edit.document())
        self.main_layout.addWidget(self.text_edit)

    def setup_menubar(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu('&File')
        self._add_file_menu_actions(file_menu)
        
        edit_menu = menubar.addMenu('&Edit')
        self._add_edit_menu_actions(edit_menu)
        
        view_menu = menubar.addMenu('&View')
        self._add_view_menu_actions(view_menu)
        
        help_menu = menubar.addMenu('&Help')
        self._add_help_menu_actions(help_menu)

    def _add_file_menu_actions(self, menu):
        open_action = QAction('&Open...', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.select_file)
        menu.addAction(open_action)

        self.recent_files_menu = menu.addMenu("Recent Files")
        self.update_recent_files_menu()
        
        save_action = QAction('&Save As...', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_assembly)
        menu.addAction(save_action)
        
        menu.addSeparator()
        
        exit_action = QAction('&Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)

    def _add_edit_menu_actions(self, menu):
        undo_action = QAction('Undo', self)
        undo_action.setShortcut('Ctrl+Z')
        undo_action.triggered.connect(self.text_edit.undo)
        menu.addAction(undo_action)

        redo_action = QAction('Redo', self)
        redo_action.setShortcut('Ctrl+Y')
        redo_action.triggered.connect(self.text_edit.redo)
        menu.addAction(redo_action)

    def _add_view_menu_actions(self, menu):
        zoom_in_action = QAction('Zoom &In', self)
        zoom_in_action.setShortcut('Ctrl++')
        zoom_in_action.triggered.connect(lambda: self.text_edit.zoomIn(2))
        menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction('Zoom &Out', self)
        zoom_out_action.setShortcut('Ctrl+-')
        zoom_out_action.triggered.connect(lambda: self.text_edit.zoomOut(2))
        menu.addAction(zoom_out_action)

        menu.addSeparator()

        font_action = QAction('&Change Font...', self)
        font_action.triggered.connect(self.change_font)
        menu.addAction(font_action)

    def _add_help_menu_actions(self, menu):
        about_action = QAction('&About', self)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)

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
            'License: MIT\n'
            )
            
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

    def update_recent_files_menu(self):
        self.recent_files_menu.clear()
        recent_files = self.settings.value("recent_files", [])
        
        if not recent_files:
            empty_action = QAction("No recent files", self)
            empty_action.setEnabled(False)
            self.recent_files_menu.addAction(empty_action)
            return

        for file_path in recent_files:
            action = QAction(file_path, self)
            action.triggered.connect(lambda checked, path=file_path: self.open_recent_file(path))
            self.recent_files_menu.addAction(action)
        
    def select_file(self):
        last_dir = self.settings.value('last_directory', '')
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            last_dir,
            ".exe Files (*.exe *.elf *.bin *.pe *.asm)"
        )
        
        if file_path:
            self.settings.setValue('last_directory', os.path.dirname(file_path))
            self.current_file = file_path
            self.update_recent_files(file_path)
            self.setWindowTitle(f"{self.base_title} - {os.path.basename(file_path)}")
            self.file_label.setText(file_path)
            self.status_bar.showMessage(f"Loading {os.path.basename(file_path)}...")
            self.start_decompile(file_path)

    def update_recent_files(self, file_path):
        recent_files = self.settings.value("recent_files", [])
        if file_path in recent_files:
            recent_files.remove(file_path)
        recent_files.insert(0, file_path)
        recent_files = recent_files[:10]
        self.settings.setValue("recent_files", recent_files)
        self.update_recent_files_menu()

    def open_recent_file(self, file_path):
        if os.path.exists(file_path):
            self.current_file = file_path
            self.update_recent_files(file_path)
            self.setWindowTitle(f"{self.base_title} - {os.path.basename(file_path)}")
            self.file_label.setText(file_path)
            self.status_bar.showMessage(f"Loading {os.path.basename(file_path)}...")
            self.start_decompile(file_path)
        else:
            QMessageBox.warning(self, "File Not Found", f"The file {file_path} could not be found.")


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
        self.text_edit.setPlainText(error_msg)
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