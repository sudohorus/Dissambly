import subprocess
import re
from PyQt6.QtCore import QThread, pyqtSignal

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