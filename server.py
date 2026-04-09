from signal import signal
import socket
import time
import threading
import selectors
import logging
import os
import signal

lock = threading.Lock()

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)

sel = selectors.DefaultSelector()

def signal_handler(sig, frame):
    logging.info("Sinal SIGINT recebido, encerrando servidor...")
    sel.close()
    os._exit(0)
    

def handle_client(conn, addr):
    logging.info(f"Cliente conectado: {addr}")
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            try:
                # CADRASTRO user, password
                if data.decode().startswith("CADASTRO"):
                    logging.info(f"Comando CADASTRO recebido de {addr}")
                    user, password = data.decode()[9:].split(",")
                    with lock:
                        with open("users.txt", "a") as f:
                            f.write(f"{user},{password}\n")
                        os.mkdir(f"users/{user}")
                    conn.sendall(b"USER_REGISTERED")

                # CONNECT user, password
                elif data.decode().startswith("CONNECT"):
                    logging.info(f"Comando CONNECT recebido de {addr}")
                    user, password = data.decode()[8:].split(",")
                    with lock:
                         with open("users.txt", "r") as f:
                            users = f.readlines()
                    users = [u.strip().split(",") for u in users]
                    if [user, password] in users:
                        conn.sendall(b"USER_AUTHENTICATED")
                        os.chdir(f"users/{user}")
                    else:
                        conn.sendall(b"AUTHENTICATION_FAILED")

                # EXIT
                elif data.decode().startswith("EXIT"):
                    logging.info(f"Comando EXIT recebido de {addr}")
                    conn.sendall(b"")
                    conn.close()
                    break

                # PWD
                elif data.decode().startswith("PWD"):
                    logging.info(f"Comando PWD recebido de {addr}")
                    conn.sendall(os.getcwd().encode())

                # GETDIRS
                elif data.decode().startswith("GETDIRS"):
                    logging.info(f"Comando GETDIRS recebido de {addr}")
                    dirs = [d for d in os.listdir() if os.path.isdir(d)]
                    conn.sendall(",".join(dirs).encode())

                # GETFILES
                elif data.decode().startswith("GETFILES"):
                    logging.info(f"Comando GETFILES recebido de {addr}")
                    files = [f for f in os.listdir() if os.path.isfile(f)]
                    conn.sendall(",".join(files).encode())


                else:
                    logging.info(f"Mensagem recebida de {addr}: {data.decode()}")
                    conn.sendall(f"{data.decode()}".encode())

            except Exception as e:
                logging.error(f"Erro ao processar mensagem de {addr}: {e}")
                conn.sendall(b"ERROR_PROCESSING_MESSAGE")

        except ConnectionResetError:
            logging.info(f"Cliente desconectado: {addr}")
            break
    conn.close()
    logging.info(f"Conexão encerrada: {addr}")

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        logging.info(f"Servidor executando em {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr)).start()
            logging.info(f"Nova conexão de {addr}")

if "__main__" == __name__:
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.info("Iniciando servidor")

    signal.signal(signal.SIGINT, signal_handler)

    main()
