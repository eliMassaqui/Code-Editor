from pyfirmata2 import Arduino
import time

def conectar_arduino():
    print("\n[ BUSCANDO ] Procurando Arduino...")
    try:
        board = Arduino(Arduino.AUTODETECT)
        time.sleep(2)
        print("[ OK ] Arduino conectado!")
        return board
    except Exception as e:
        raise e

def piscar_led(board):
    led = board.get_pin('d:13:o')
    print("[ RODANDO ] Pisca-pisca iniciado (Ctrl + C para sair)\n")

    while True:
        led.write(1)
        print("LED LIGADO")
        time.sleep(1)

        led.write(0)
        print("LED DESLIGADO")
        time.sleep(1)

if __name__ == "__main__":
    while True:
        board = None
        try:
            board = conectar_arduino()
            piscar_led(board)

        except KeyboardInterrupt:
            print("\n[ SAÍDA ] Programa finalizado pelo usuário.")
            break

        except Exception:
            print("\n[ ERRO ] Arduino desconectado. Tentando novamente em 3s...")
            time.sleep(3)

        finally:
            if board:
                board.exit()
                print("[ INFO ] Conexão encerrada com segurança.")
