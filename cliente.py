import socket
import logging
import time

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 65432  # The port used by the server

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as c:
        c.connect((HOST, PORT))
        while True:
            message = input("Digite uma mensagem para enviar ao servidor: ")
            c.sendall(message.encode())
            data = c.recv(1024)
            logging.info(f"Resposta do servidor: {data.decode()}")

            if not data:
                break

    logging.info("conexão encerrada")

if "__main__" == __name__:
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.info("Iniciando cliente")
    main()