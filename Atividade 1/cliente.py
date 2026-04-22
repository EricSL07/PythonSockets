"""Cliente de socket que se conecta a um servidor TCP.

Este cliente permite que o usuário envie mensagens para um servidor
e receba respostas. Suporta comandos como CADASTRO, CONNECT, PWD, GETFILES, etc.
"""

import socket
import logging
import time

HOST = "127.0.0.1"  # Endereço do servidor (localhost)
PORT = 65432  # Porta para conectar ao servidor

def main():
    """Função principal que estabelece conexão e gerencia comunicação.
    
    Conecta ao servidor no HOST e PORT especificados, permite que o usuário
    digite mensagens continuamente e exibe as respostas do servidor.
    A conexão se encerra quando o servidor não retorna dados.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as c:
        # Estabelece conexão com o servidor
        c.connect((HOST, PORT))
        while True:
            # Recebe entrada do usuário
            message = input("Digite uma mensagem para enviar ao servidor: ")
            # Codifica e envia a mensagem
            c.sendall(message.encode())
            # Recebe resposta do servidor
            data = c.recv(1024)
            logging.info(f"Resposta do servidor: {data.decode()}")

            # Encerra se não receber dados
            if not data:
                break

    logging.info("conexão encerrada")

if "__main__" == __name__:
    # Configura logging para exibir hora, minuto e segundo
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.info("Iniciando cliente")
    main()