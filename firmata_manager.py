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

    def _preparar_config_wifi(self, caminho_sketch):
        config_file = os.path.join(caminho_sketch, "wifiConfig.h")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    lines = f.readlines()
                with open(config_file, 'w') as f:
                    for line in lines:
                        if "define ARDUINO_WIFI_SHIELD" in line and "//" in line[:10]:
                            f.write(line.replace("//", "", 1))
                        else:
                            f.write(line)
                self.log_received.emit("[SISTEMA] Configuração WiFi ajustada.\n")
            except: pass

    def _get_sketch_path(self, tipo):
        libraries_path = os.path.expanduser("~/Documents/Arduino/libraries")
        
        # MAPEAMENTO CORRIGIDO PARA EVITAR "MAIN FILE MISSING"
        # Agora apontamos para a pasta que contém o .ino de mesmo nome
        mapeamento = {
            "Standard": ("Firmata", "examples/StandardFirmata"),
            "Plus": ("Firmata", "examples/StandardFirmataPlus"),
            "Configurable": ("ConfigurableFirmata", "examples/ConfigurableFirmata"), # Pasta de exemplo tem o nome correto
            "Wifi": ("Firmata", "examples/StandardFirmataWiFi")
        }
        
        if tipo not in mapeamento: return None
        pasta_lib, sub = mapeamento[tipo]
        
        caminho_completo = os.path.join(libraries_path, pasta_lib, sub)

        if not os.path.exists(caminho_completo):
            # Fallback caso a estrutura da lib Configurable seja diferente
            if tipo == "Configurable":
                caminho_completo = os.path.join(libraries_path, pasta_lib)
            
            if not os.path.exists(caminho_completo):
                self.log_received.emit(f"⚠️ Erro: Pasta '{tipo}' não encontrada.\n")
                return None
            
        return caminho_completo

    def compile_firmata(self, tipo="Standard"):
        caminho_sketch = self._get_sketch_path(tipo)
        if not caminho_sketch: return 

        if tipo == "Wifi":
            self._preparar_config_wifi(caminho_sketch)

        self.log_received.emit(f"\n[SISTEMA] Iniciando Compilação do {tipo}...\n")
        cmd = [self.cli_path, "compile", "--fqbn", self.board, caminho_sketch]
        
        self.thread = HardwareActionThread(cmd)
        self.thread.log_signal.connect(lambda t: self.log_received.emit(t + "\n"))
        self.thread.finished_signal.connect(lambda m: self.log_received.emit(m + "\n"))
        self.thread.start()

    def upload_firmata(self, porta, tipo="Standard"):
        caminho_sketch = self._get_sketch_path(tipo)
        if not caminho_sketch: return 

        self.log_received.emit(f"\n[SISTEMA] Realizando Upload do {tipo} na porta {porta}...\n")
        cmd = [self.cli_path, "upload", "-p", porta, "--fqbn", self.board, caminho_sketch]
        
        self.thread = HardwareActionThread(cmd)
        self.thread.log_signal.connect(lambda t: self.log_received.emit(t + "\n"))
        self.thread.finished_signal.connect(lambda m: self.log_received.emit(m + "\n"))
        self.thread.start()