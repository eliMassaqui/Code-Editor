import os
import shutil
import subprocess
from PyQt6.QtCore import QObject, QThread, pyqtSignal

class HardwareActionThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)

    def __init__(self, comando):
        super().__init__()
        self.comando = comando

    def run(self):
        try:
            # Flags para silenciar o console no Windows
            flags = 0x08000000 if os.name == 'nt' else 0
            p = subprocess.Popen(self.comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 text=True, creationflags=flags)
            for line in p.stdout:
                self.log_signal.emit(line.strip())
            p.wait()
            self.finished_signal.emit("✅ Operação concluída" if p.returncode == 0 else "❌ Falha na operação")
        except Exception as e:
            self.finished_signal.emit(f"❌ Erro: {str(e)}")

class FirmataManager(QObject):
    log_received = pyqtSignal(str)
    
    def __init__(self, board="arduino:avr:uno"):
        super().__init__()
        self.board = board
        self.cli_path = self._find_arduino_cli()

    def _find_arduino_cli(self):
        cli = shutil.which("arduino-cli")
        if cli: return cli
        home = os.path.expanduser("~")
        possible = [os.path.join(home, "Documents", "Wandi Studio", "Engine", "arduino", "arduino-cli.exe")]
        for p in possible:
            if os.path.exists(p): return p
        return "arduino-cli"

    def compile_firmata(self, tipo="StandardFirmata"):
        self.log_received.emit(f"\n[SISTEMA] Iniciando Compilação do {tipo}...\n")
        caminho_sketch = os.path.expanduser(f"~/Documents/Arduino/libraries/Firmata/examples/{tipo}")
        cmd = [self.cli_path, "compile", "--fqbn", self.board, caminho_sketch]
        
        self.thread = HardwareActionThread(cmd)
        self.thread.log_signal.connect(lambda t: self.log_received.emit(t + "\n"))
        self.thread.finished_signal.connect(lambda m: self.log_received.emit(m + "\n"))
        self.thread.start()

    def upload_firmata(self, porta, tipo="StandardFirmata"):
        self.log_received.emit(f"\n[SISTEMA] Realizando Upload do {tipo} na porta {porta}...\n")
        caminho_sketch = os.path.expanduser(f"~/Documents/Arduino/libraries/Firmata/examples/{tipo}")
        cmd = [self.cli_path, "upload", "-p", porta, "--fqbn", self.board, caminho_sketch]
        
        self.thread = HardwareActionThread(cmd)
        self.thread.log_signal.connect(lambda t: self.log_received.emit(t + "\n"))
        self.thread.finished_signal.connect(lambda m: self.log_received.emit(m + "\n"))
        self.thread.start()