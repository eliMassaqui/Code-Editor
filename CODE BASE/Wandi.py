import time
from pyfirmata2 import Arduino

board = Arduino(Arduino.AUTODETECT)
led = board.get_pin('d:13:o')
delay = 1000 # Equivalem a 1 segundos

def setup(): pass

def loop():
    led.write(1)
    time.sleep(delay / 1000)
    led.write(0)
    time.sleep(delay / 1000)

setup()
while True: loop()