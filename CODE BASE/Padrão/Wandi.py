import time
from pyfirmata2 import Arduino

# Configuração da placa
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