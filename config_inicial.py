import os

def inicializar_ambiente_wandi():
    """Garante a criação das pastas e do arquivo de código padrão."""
    # Caminho das pastas
    docs = os.path.join(os.path.expanduser("~"), "Documents")
    pasta_studio = os.path.join(docs, "Wandi Studio")
    pasta_code = os.path.join(pasta_studio, "Wandi Code")
    
    # Cria as pastas se não existirem
    if not os.path.exists(pasta_code):
        os.makedirs(pasta_code, exist_ok=True)
    
    # Caminho do arquivo padrão
    arquivo_py = os.path.join(pasta_code, "Wandi.py")
    
    # PONTO SEGURO PARA ALTERAÇÃO: Template de inicialização (Estilo Arduino IDE)
    codigo_arduino = """import time
from pyfirmata2 import Arduino
board = Arduino(Arduino.AUTODETECT)

def setup():
    # Coloque seu código de configuração aqui, para rodar uma vez:
    pass

def loop():
    # Coloque seu código principal aqui, para rodar repetidamente:
    pass

    # Execução
    setup()
    while True: loop()
"""

    # Cria o arquivo apenas se ele não existir
    if not os.path.exists(arquivo_py):
        with open(arquivo_py, "w", encoding="utf-8") as f:
            f.write(codigo_arduino)
            
    return pasta_code