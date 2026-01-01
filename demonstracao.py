# --- WANDI STUDIO IDE - TESTE DE SINTAXE PADRÃO ---
"""
Este é um teste de Docstring (múltiplas linhas).
Tudo aqui deve aparecer na cor de strings (verde),
incluindo estas linhas.
"""

import time
import random

class SistemaRobotico:
    def __init__(self, id_robo):
        self.id = id_robo
        self.sensores = {"ultra": 0, "infra": False}
        self.status = "Inativo"
        self.contador = 0

    @property
    def info(self):
        return f"Robo {self.id} | Status: {self.status}"

    def ler_sensores(self):
        # Números em laranja, self em roxo
        distancia = 15.5 
        self.sensores["ultra"] = distancia
        
        if distancia < 10:
            self.status = "Alerta: Objeto Próximo"
            return True
        else:
            self.status = "Caminho Livre"
            return False

def iniciar_debug():
    print("Iniciando depuração do sistema...")
    wandi = SistemaRobotico(id_robo="Wandi_01")
    
    for i in range(1, 6):
        time.sleep(0.1)
        deteccao = wandi.ler_sensores()
        
        if deteccao == True:
            print(f"Ciclo {i}: {wandi.info}")
            break
        else:
            print(f"Ciclo {i}: Operação Normal")

if __name__ == "__main__":
    try:
        iniciar_debug()
    except Exception as e:
        print(f"Erro detectado: {e}")