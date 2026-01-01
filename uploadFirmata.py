import sys
import os
import platform
import subprocess
import shutil
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel,
    QProgressBar, QComboBox
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

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
else:
    ARDUINO_PATH = os.path.expanduser("~/Arduino")

EXAMPLES_PATH = os.path.join(ARDUINO_PATH, "libraries", "Firmata", "examples", FIRMATA_SKETCH)
PORT_COMMAND = [ARDUINO_CLI, "board", "list"]

# ================= THREADS =================
class CompileThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)

    def run(self):
        try:
            self.progress_signal.emit(0)
            self.check_arduino_cli()
            self.progress_signal.emit(1)
            self.install_core_and_servo()
            self.progress_signal.emit(2)
            self.compile_firmata()
            self.progress_signal.emit(3)
            self.finished_signal.emit("✅ Compilação concluída com sucesso.")
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
            raise RuntimeError(f"arduino-cli não encontrado em {ARDUINO_CLI}")
        self.run_cmd([ARDUINO_CLI, "version"])
        self.log_signal.emit("arduino-cli verificado com sucesso.")

    def install_core_and_servo(self):
        self.run_cmd([ARDUINO_CLI, "core", "install", "arduino:avr"])
        self.run_cmd([ARDUINO_CLI, "lib", "install", "Servo"])
        self.log_signal.emit("Core e biblioteca Servo instalados com sucesso.")

    def compile_firmata(self):
        if not os.path.exists(EXAMPLES_PATH):
            raise RuntimeError(f"StandardFirmata não encontrado em {EXAMPLES_PATH}")
        self.run_cmd([ARDUINO_CLI, "compile", "--fqbn", BOARD, EXAMPLES_PATH])
        self.log_signal.emit("Firmata compilado com sucesso.")

class UploadThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)

    def __init__(self, port):
        super().__init__()
        self.port = port

    def run(self):
        try:
            self.progress_signal.emit(0)
            if not self.port:
                raise RuntimeError("Nenhuma porta selecionada.")
            self.progress_signal.emit(1)
            self.upload_firmata(self.port)
            self.progress_signal.emit(2)
            self.finished_signal.emit("✅ Upload concluído com sucesso.")
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

    def upload_firmata(self, port):
        self.run_cmd([ARDUINO_CLI, "upload", "-p", port, "--fqbn", BOARD, EXAMPLES_PATH])
        self.log_signal.emit(f"Firmata enviado para o Arduino na porta {port} com sucesso.")

# ================= INTERFACE =================
class FirmataGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StandardFirmata - Deep Blue IDE")
        self.setGeometry(100, 100, 800, 500)
        self.selected_port = None
        self.init_ui()
        self.setStyleSheet(self.deep_blue_style())
        self.refresh_ports()

    def init_ui(self):
        layout = QVBoxLayout()

        self.label = QLabel("Compile e carregue o StandardFirmata no Arduino Uno")
        self.label.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 14pt;")
        layout.addWidget(self.label)

        # Dropdown de portas
        self.port_dropdown = QComboBox()
        self.port_dropdown.setToolTip("Selecione a porta do Arduino")
        self.port_dropdown.currentIndexChanged.connect(self.port_selected)
        # Corrigido para PyQt6: atualiza ao abrir o menu
        self.port_dropdown.showPopup = self.combo_show_popup
        layout.addWidget(self.port_dropdown)

        # Botões de Compile e Upload
        self.compile_button = QPushButton("Compilar Firmata")
        self.compile_button.clicked.connect(self.start_compile)
        layout.addWidget(self.compile_button)

        self.upload_button = QPushButton("Carregar na Placa")
        self.upload_button.clicked.connect(self.start_upload)
        layout.addWidget(self.upload_button)

        # Barra de progresso
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminada
        self.progress.setVisible(False)
        self.progress.setStyleSheet(
            "QProgressBar {background-color: #1C2B3A; border: 1px solid #0A1A28; height: 20px;} "
            "QProgressBar::chunk {background-color: #00FFDD;}"
        )
        layout.addWidget(self.progress)

        # Log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", 10))
        self.log.setStyleSheet("background-color: #0B1622; color: #00FFDD;")
        layout.addWidget(self.log)

        self.setLayout(layout)

    # ---------------------- Dropdown de portas ----------------------
    def combo_show_popup(self):
        self.refresh_ports()
        QComboBox.showPopup(self.port_dropdown)

    def refresh_ports(self):
        current_text = self.port_dropdown.currentText()
        self.port_dropdown.clear()
        ports = self.list_ports()
        if not ports:
            self.append_log("Nenhum Arduino detectado.", "#FF5555")
        for port in ports:
            self.port_dropdown.addItem(port)
        if ports:
            # Tenta manter a seleção anterior
            if current_text in ports:
                self.port_dropdown.setCurrentText(current_text)
                self.selected_port = current_text
            else:
                self.selected_port = ports[0]
                self.append_log(f"Porta selecionada automaticamente: {self.selected_port}", "#00FFDD")

    def list_ports(self):
        try:
            output = subprocess.run([ARDUINO_CLI, "board", "list"], capture_output=True, text=True)
            lines = output.stdout.splitlines()
            ports = []
            for line in lines:
                if platform.system() == "Windows" and "COM" in line:
                    ports.append(line.split()[0])
                elif platform.system() != "Windows" and "/dev/tty" in line:
                    ports.append(line.split()[0])
            return ports
        except Exception as e:
            self.append_log(f"Erro ao listar portas: {e}", "#FF5555")
            return []

    def port_selected(self, index):
        self.selected_port = self.port_dropdown.currentText()
        self.append_log(f"Porta selecionada: {self.selected_port}", "#00FFDD")

    # ---------------------- Logs ----------------------
    def append_log(self, text, color="#00FFDD"):
        self.log.setTextColor(QColor(color))
        self.log.append(text)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    # ---------------------- Botões ----------------------
    def start_compile(self):
        self.compile_button.setEnabled(False)
        self.upload_button.setEnabled(False)
        self.progress.setVisible(True)
        self.log.clear()

        self.compile_thread = CompileThread()
        self.compile_thread.log_signal.connect(lambda text: self.append_log(text))
        self.compile_thread.finished_signal.connect(self.compile_finished)
        self.compile_thread.start()

    def start_upload(self):
        self.upload_button.setEnabled(False)
        self.progress.setVisible(True)
        self.upload_thread = UploadThread(self.selected_port)
        self.upload_thread.log_signal.connect(lambda text: self.append_log(text))
        self.upload_thread.finished_signal.connect(self.upload_finished)
        self.upload_thread.start()

    def compile_finished(self, message):
        color = "#00FF00" if "sucesso" in message.lower() else "#FF5555"
        self.append_log(message, color)
        self.progress.setVisible(False)
        self.compile_button.setEnabled(True)
        self.upload_button.setEnabled(True)

    def upload_finished(self, message):
        color = "#00FF00" if "sucesso" in message.lower() else "#FF5555"
        self.append_log(message, color)
        self.progress.setVisible(False)
        self.upload_button.setEnabled(True)

    # ---------------------- Estilo ----------------------
    def deep_blue_style(self):
        return """
        QWidget { background-color: #0B1622; }
        QPushButton { background-color: #1C2B3A; color: #00FFDD; border: 1px solid #0A1A28; padding: 8px; font-weight: bold; }
        QPushButton:hover { background-color: #2A3B50; }
        QLabel { color: #00FFDD; }
        QComboBox { background-color: #1C2B3A; color: #00FFDD; border: 1px solid #0A1A28; padding: 5px; }
        QComboBox:hover { background-color: #2A3B50; }
        """

# ================= EXECUÇÃO =================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FirmataGUI()
    window.show()
    sys.exit(app.exec())
