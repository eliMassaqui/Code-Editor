import pyfirmata2
import time

# Conecta automaticamente ao Arduino
board = pyfirmata2.Arduino(pyfirmata2.Arduino.AUTODETECT)

print("Conectado ao Arduino!")

try:
    while True:
        board.digital[13].write(1)  # Liga o LED
        print("LED Aceso")
        time.sleep(1)
        
        board.digital[13].write(0)  # Desliga o LED
        print("LED Apagado")
        time.sleep(1)
except KeyboardInterrupt:
    # Fecha a conexão ao pressionar Ctrl+C
    board.exit()