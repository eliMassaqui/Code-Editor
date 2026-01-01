import sys, os, subprocess, requests, zipfile, platform, json, datetime, socket
from PyQt6.QtWidgets import (QVBoxLayout, QWidget, QTextEdit, 
                             QProgressBar, QLabel)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QTextCursor

# --- CONSTANTES DE ESTILO (Preservando seu padrão) ---
COLOR_BG = "#0b1622"
COLOR_EDITOR = "#152233"
COLOR_CONSOLE = "#050a0f"
COLOR_ACCENT = "#3498db"
COLOR_TEXT = "#d1dce8"

class EngineWorker(QThread):
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal()

    def __init__(self, cli_path, work_dir):
        super().__init__()
        self.cli_path = cli_path
        self.work_dir = work_dir

    def check_internet(self):
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False

    def log(self, text, status="info", delay=600):
        """ Envia o log e aguarda um tempo para leitura """
        t = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_signal.emit(f"[{t}] {text}", status)
        self.msleep(delay)

    def run(self):
        temp_zip = os.path.join(self.work_dir, "arduino_cli_temp.zip")
        # Flag para silenciar janelas de console no Windows
        flags = 0x08000000 if os.name == 'nt' else 0

        try:
            self.log("Iniciando Verificação de Engine...", "proc", 1000)
            
            if not self.check_internet():
                self.log("AVISO: Sem conexão com a internet.", "err", 1500)
                self.log("Algumas atualizações serão ignoradas.", "info", 1000)
            else:
                self.log("Conexão com a rede: OK", "ok", 800)

            # 1. DOWNLOAD DO CORE CLI (Se necessário)
            if not os.path.exists(self.cli_path):
                if not self.check_internet():
                    self.log("ERRO CRÍTICO: Engine não encontrada.", "err", 1500)
                    return 

                self.log("Engine Ausente. Baixando Core...", "proc", 1000)
                url = "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Windows_64bit.zip"
                r = requests.get(url, stream=True)
                total = int(r.headers.get('content-length', 0))
                
                dl = 0
                with open(temp_zip, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                        dl += len(chunk)
                        if total > 0: self.progress_signal.emit(int((dl/total)*100))
                
                self.log("Download concluído. Extraindo...", "proc", 1200)
                with zipfile.ZipFile(temp_zip, 'r') as z:
                    z.extractall(self.work_dir)
                os.remove(temp_zip)
                self.log("Instalação do binário finalizada.", "ok", 1000)
            else:
                self.log("Localizando arquivos da Engine...", "proc", 600)
                self.progress_signal.emit(20)
                self.log("Engine carregada com sucesso.", "ok", 800)

            # 2. INSTALAÇÃO DE PLACAS E DEPENDÊNCIAS (Somente Online)
            if self.check_internet():
                self.log("Sincronizando banco de dados...", "proc", 1000)
                subprocess.run([self.cli_path, "core", "update-index"], shell=True, capture_output=True, creationflags=flags)
                self.progress_signal.emit(30)
                
                self.log("Verificando arquiteturas AVR (Arduino)...", "proc", 1000)
                subprocess.run([self.cli_path, "core", "install", "arduino:avr"], shell=True, capture_output=True, creationflags=flags)
                self.progress_signal.emit(40)

                # --- BLOCO DE BLINDAGEM: REQUISITOS TÉCNICOS ---
                self.log("Sincronizando Hardware Helper Libs...", "info", 600)
                # Estas libs evitam erros de "No such file" em Standard e Plus
                deps = ["Servo", "Wire", "Stepper", "LiquidCrystal", 
                        "Adafruit Unified Sensor", "DHT sensor library", "NewPing"]
                
                for dep in deps:
                    self.log(f"Instalando componente: {dep}...", "proc", 300)
                    subprocess.run([self.cli_path, "lib", "install", dep], 
                                   shell=True, capture_output=True, creationflags=flags)
                self.progress_signal.emit(60)

                # --- INSTALAÇÃO DAS FIRMATAS DO CARD ---
                self.log("Sincronizando Firmatas Principais...", "info", 800)
                
                firmatas = [
                    ("Firmata", "Standard", 70),
                    ("FirmataPlus", "Plus", 80),
                    ("ConfigurableFirmata", "Configurable", 90)
                ]

                for lib, nome, prog in firmatas:
                    self.log(f"Preparando {lib} ({nome})...", "proc", 600)
                    subprocess.run([self.cli_path, "lib", "install", lib], 
                                   shell=True, capture_output=True, creationflags=flags)
                    self.progress_signal.emit(prog)

                # Bibliotecas para WiFi Firmata
                self.log("Preparando protocolos WiFi/Ethernet...", "proc", 600)
                subprocess.run([self.cli_path, "lib", "install", "WiFi"], shell=True, capture_output=True, creationflags=flags)
                subprocess.run([self.cli_path, "lib", "install", "Ethernet"], shell=True, capture_output=True, creationflags=flags)
                self.progress_signal.emit(95)
            else:
                self.log("Modo Offline: Usando dependências locais.", "info", 1500)
            
            # 3. FINALIZAÇÃO
            self.log("Escaneando portas USB por hardware...", "proc", 800)
            subprocess.run([self.cli_path, "board", "list", "--format", "json"], 
                           capture_output=True, text=True, shell=True, creationflags=flags)
            
            self.log("ENGINE E HARDWARE SINCRONIZADOS.", "ok", 800)
            self.log("WANDI STUDIO PRONTO.", "ok", 500)
            self.progress_signal.emit(100)

        except Exception as e:
            self.log(f"ERRO DE SISTEMA: {str(e)}", "err", 3000)
        finally:
            self.finished_signal.emit()

class ArduinoEngineOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(480, 160)
        
        self.setStyleSheet(f"""
            QWidget#MainContainer {{
                background-color: {COLOR_EDITOR};
                border: 2px solid {COLOR_ACCENT};
                border-radius: 6px;
            }}
            QLabel {{ 
                color: {COLOR_ACCENT}; font-family: 'Consolas'; font-size: 13px; 
                font-weight: bold; background: transparent; border: none;
            }}
            QProgressBar {{
                border: 1px solid {COLOR_BG}; border-radius: 2px; text-align: center;
                background-color: {COLOR_CONSOLE}; color: {COLOR_TEXT};
                height: 12px; font-size: 10px;
            }}
            QProgressBar::chunk {{ background-color: {COLOR_ACCENT}; }}
            QTextEdit {{ 
                background: transparent; border: none; color: {COLOR_TEXT}; 
                font-family: 'Consolas'; font-size: 11px; 
            }}
        """)
        
        self.container = QWidget(self)
        self.container.setObjectName("MainContainer")
        self.container.setFixedSize(self.size())
        
        layout = QVBoxLayout(self.container)
        self.title = QLabel("WANDI ENGINE SYSTEM")
        self.pbar = QProgressBar()
        self.pbar.setRange(0, 100)
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        layout.addWidget(self.title)
        layout.addWidget(self.pbar)
        layout.addWidget(self.console)

    def iniciar(self):
        user_docs = os.path.join(os.path.expanduser('~'), "Documents")
        work_dir = os.path.join(user_docs, "Wandi Studio", "Engine", "arduino")
        os.makedirs(work_dir, exist_ok=True)
        cli_path = os.path.join(work_dir, "arduino-cli.exe")

        self.show()
        self.posicionar_no_canto()
        
        self.worker = EngineWorker(cli_path, work_dir)
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.pbar.setValue)
        self.worker.finished_signal.connect(lambda: QTimer.singleShot(6000, self.hide))
        self.worker.start()

    def append_log(self, text, status):
        colors = {"info": "#888888", "ok": "#00ff00", "err": "#ff3333", "proc": COLOR_ACCENT}
        color = colors.get(status, COLOR_TEXT)
        self.console.append(f'<span style="color: {color};">{text}</span>')
        self.console.moveCursor(QTextCursor.MoveOperation.End)

    def posicionar_no_canto(self):
        if self.parentWidget():
            p = self.parentWidget().rect()
            x = p.width() - self.width() - 20
            y = p.height() - self.height() - 45 
            self.move(x, y)
            self.raise_()