import sys
import os
import platform
import subprocess
import shutil
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel, QProgressBar
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QFont

# ================= CONFIGURAÇÕES =================
BOARD = "arduino:avr:uno"
FIRMATA_SKETCH = "StandardFirmata"

# ================= DETECÇÃO AUTOMÁTICA DO ARDUINO CLI =================
def find_arduino_cli():
    cli_path = shutil.which("arduino-cli")
    if cli_path:
        return cli_path

    home = os.path.expanduser("~")
    possible_paths = [
        os.path.join(home, "Documents", "Wandi Studio", "Engine", "arduino", "arduino-cli.exe"),
        os.path.join(home, "Wandi Studio", "Engine", "arduino", "arduino-cli.exe")
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path

    raise FileNotFoundError(
        "arduino-cli.exe não encontrado. Instale no PATH ou coloque em Wandi Studio/Engine/arduino/"
    )

ARDUINO_CLI = find_arduino_cli()

# Caminho do Arduino
if platform.system() == "Windows":
    ARDUINO_PATH = os.path.expanduser("~/Documents/Arduino")
    PORT_COMMAND = [ARDUINO_CLI, "board", "list"]
else:
    ARDUINO_PATH = os.path.expanduser("~/Arduino")
    PORT_COMMAND = [ARDUINO_CLI, "board", "list"]

EXAMPLES_PATH = os.path.join(ARDUINO_PATH, "libraries", "Firmata", "examples", FIRMATA_SKETCH)

# ================= THREADS =================
class CompileThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)

    def run(self):
        try:
            self.check_arduino_cli()
            self.install_core_and_servo()
            self.compile_firmata()
            self.finished_signal.emit("✅ Compilação concluída!")
        except Exception as e:
            self.finished_signal.emit(f"❌ Erro: {e}")

    def run_cmd(self, cmd):
        self.log_signal.emit(f">> {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            self.log_signal.emit(line.strip())
        process.wait()
        if process.returncode != 0:
            raise RuntimeError(f"Comando falhou: {' '.join(cmd)}")

    def check_arduino_cli(self):
        if not os.path.exists(ARDUINO_CLI):
            raise RuntimeError(f"arduino-cli.exe não encontrado em {ARDUINO_CLI}")
        self.run_cmd([ARDUINO_CLI, "version"])

    def install_core_and_servo(self):
        self.run_cmd([ARDUINO_CLI, "core", "install", "arduino:avr"])
        self.run_cmd([ARDUINO_CLI, "lib", "install", "Servo"])

    def compile_firmata(self):
        if not os.path.exists(EXAMPLES_PATH):
            raise RuntimeError(f"StandardFirmata não encontrado em {EXAMPLES_PATH}")
        self.run_cmd([ARDUINO_CLI, "compile", "--fqbn", BOARD, EXAMPLES_PATH])


class UploadThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)

    def run(self):
        try:
            port = self.detect_port()
            self.upload_firmata(port)
            self.finished_signal.emit("✅ Upload concluído!")
        except Exception as e:
            self.finished_signal.emit(f"❌ Erro: {e}")

    def run_cmd(self, cmd):
        self.log_signal.emit(f">> {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            self.log_signal.emit(line.strip())
        process.wait()
        if process.returncode != 0:
            raise RuntimeError(f"Comando falhou: {' '.join(cmd)}")

    def detect_port(self):
        output = subprocess.run(PORT_COMMAND, capture_output=True, text=True)
        lines = output.stdout.splitlines()
        for line in lines:
            if "arduino" in line.lower():
                port = line.split()[0]
                self.log_signal.emit(f"✅ Arduino detectado na porta {port}")
                return port
        raise RuntimeError("Não foi possível detectar o Arduino.")

    def upload_firmata(self, port):
        # Upload direto do sketch, sem precisar do caminho HEX fixo
        self.run_cmd([ARDUINO_CLI, "upload", "-p", port, "--fqbn", BOARD, EXAMPLES_PATH])


# ================= INTERFACE DEEP BLUE =================
class FirmataGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StandardFirmata - Deep Blue IDE")
        self.setGeometry(100, 100, 800, 500)
        self.init_ui()
        self.setStyleSheet(self.deep_blue_style())

    def init_ui(self):
        layout = QVBoxLayout()

        self.label = QLabel("Compile e carregue o StandardFirmata no Arduino Uno")
        self.label.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 14pt;")
        layout.addWidget(self.label)

        self.compile_button = QPushButton("💻 Compilar Firmata")
        self.compile_button.clicked.connect(self.start_compile)
        layout.addWidget(self.compile_button)

        self.upload_button = QPushButton("📤 Carregar na Placa")
        self.upload_button.clicked.connect(self.start_upload)
        layout.addWidget(self.upload_button)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setStyleSheet(
            "QProgressBar {background-color: #1C2B3A; border: 1px solid #0A1A28; height: 20px;}"
        )
        layout.addWidget(self.progress)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", 10))
        self.log.setStyleSheet("background-color: #0B1622; color: #00FFDD;")
        layout.addWidget(self.log)

        self.setLayout(layout)

    def deep_blue_style(self):
        return """
        QWidget {
            background-color: #0B1622;
        }
        QPushButton {
            background-color: #1C2B3A;
            color: #00FFDD;
            border: 1px solid #0A1A28;
            padding: 8px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2A3B50;
        }
        QLabel {
            color: #00FFDD;
        }
        QProgressBar::chunk {
            background-color: #00FFDD;
        }
        """

    def start_compile(self):
        self.compile_button.setEnabled(False)
        self.upload_button.setEnabled(False)
        self.progress.setVisible(True)
        self.log.clear()

        self.compile_thread = CompileThread()
        self.compile_thread.log_signal.connect(self.append_log)
        self.compile_thread.finished_signal.connect(self.compile_finished)
        self.compile_thread.start()

    def start_upload(self):
        self.upload_button.setEnabled(False)
        self.progress.setVisible(True)

        self.upload_thread = UploadThread()
        self.upload_thread.log_signal.connect(self.append_log)
        self.upload_thread.finished_signal.connect(self.upload_finished)
        self.upload_thread.start()

    def append_log(self, text):
        self.log.append(text)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def compile_finished(self, message):
        self.append_log(message)
        self.progress.setVisible(False)
        self.compile_button.setEnabled(True)
        self.upload_button.setEnabled(True)

    def upload_finished(self, message):
        self.append_log(message)
        self.progress.setVisible(False)
        self.upload_button.setEnabled(True)


# ================= EXECUÇÃO =================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FirmataGUI()
    window.show()
    sys.exit(app.exec())
