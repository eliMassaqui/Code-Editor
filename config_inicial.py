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
    arquivo_py = os.path.join(pasta_code, "wandicode.py")
    
    # Conteúdo do código para o Arduino
    codigo_arduino = """from pyfirmata2 import Arduino
import time

def conectar_arduino():
    print("\\n[ BUSCANDO ] Procurando Arduino...")
    try:
        board = Arduino(Arduino.AUTODETECT)
        time.sleep(2)
        print("[ OK ] Arduino conectado!")
        return board
    except Exception as e:
        raise e

def piscar_led(board):
    led = board.get_pin('d:13:o')
    print("[ RODANDO ] Pisca-pisca iniciado (Ctrl + C para sair)\\n")

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
            print("\\n[ SAÍDA ] Programa finalizado pelo usuário.")
            break

        except Exception:
            print("\\n[ ERRO ] Arduino desconectado. Tentando novamente em 3s...")
            time.sleep(3)

        finally:
            if board:
                board.exit()
                print("[ INFO ] Conexão encerrada com segurança.")
"""

    # Cria o arquivo apenas se ele não existir (evita sobrescrever alterações do usuário)
    if not os.path.exists(arquivo_py):
        with open(arquivo_py, "w", encoding="utf-8") as f:
            f.write(codigo_arduino)
            
    return pasta_code