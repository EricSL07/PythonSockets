from signal import signal
import socket
import time
import threading
import selectors
import logging
import os
import signal
import sys

lock = threading.Lock()

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)
PASTA_SERVIDOR = "servidor_files"

STATUS_SUCCESS = 1
STATUS_ERRORS = 2

REQUEST_MESSAGE = 1
RESPONSE_MESSAGE = 2

os.makedirs(PASTA_SERVIDOR, exist_ok=True)

sel = selectors.DefaultSelector()



def cadastro_comando(conn, addr, args):
    logging.info(f"Comando CADASTRO recebido de {addr}")
    user, password = args.split(",")
    with lock:
        with open("users.txt", "a") as f:
            f.write(f"{user},{password}\n")
            os.mkdir(f"users/{user}")
            conn.sendall(b"USER_REGISTERED")


def connect_comando(conn, addr, args):
    logging.info(f"Comando CONNECT recebido de {addr}")
    user, password = args.split(",")
    with lock:
        with open("users.txt", "r") as f:
            users = f.readlines()
    users = [u.strip().split(",") for u in users]
    if [user, password] in users:
        conn.sendall(b"USER_AUTHENTICATED")
        os.chdir(f"users/{user}")
    else:
        conn.sendall(b"AUTHENTICATION_FAILED")


def exit_comando(conn, addr, args):
    logging.info(f"Comando EXIT recebido de {addr}")
    conn.sendall(b"")
    conn.close()


def pwd_comando(conn, addr, args):
    logging.info(f"Comando PWD recebido de {addr}")
    conn.sendall(os.getcwd().encode())


def getdirs_comando(conn, addr, args):
    logging.info(f"Comando GETDIRS recebido de {addr}")
    dirs = [d for d in os.listdir() if os.path.isdir(d)]
    conn.sendall(",".join(dirs).encode())


def getfiles_comando(conn, addr, args):
    logging.info(f"Comando GETFILES recebido de {addr}")
    files = [f for f in os.listdir() if os.path.isfile(f)]
    conn.sendall(",".join(files).encode())

def addfiles_comando(conn, addr, args):
    logging.info(f"Comando ADDFILES recebido de {addr}")
    filename, content = args.split(",", 1)
    with lock:
        with open(filename, "w") as f:
            f.write(content)
        conn.sendall(b"FILE_CREATED")

def deletefiles_comando(conn, addr, args):
    logging.info(f"Comando DELETEFILES recebido de {addr}")
    filename = args.strip()
    with lock:
        if os.path.exists(filename):
            os.remove(filename)
            conn.sendall(b"FILE_DELETED")
        else:
            conn.sendall(b"FILE_NOT_FOUND")

def getfileslist_comando(conn, addr, args):
    logging.info(f"Comando GETFILESLIST recebido de {addr}")
    files = [f for f in os.listdir() if os.path.isfile(f)]
    conn.sendall(",".join(files).encode())

def getfile_comando(conn, addr, args):
    logging.info(f"Comando GETFILE recebido de {addr}")
    filename = args.strip()
    with lock:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                content = f.read()
            conn.sendall(content.encode())
        else:
            conn.sendall(b"FILE_NOT_FOUND")

comandos = {
    "CADASTRO": cadastro_comando,
    "CONNECT": connect_comando,
    "EXIT": exit_comando,
    "PWD": pwd_comando,
    "GETDIRS": getdirs_comando,
    "GETFILES": getfiles_comando,
    "ADDFILES": addfiles_comando,
    "DELETEFILES": deletefiles_comando,
    "GETFILESLIST": getfileslist_comando,
    "GETFILE": getfile_comando
}


def comando_digitado(data):
    for comando in comandos:
        if data.startswith(comando):
            args = data[len(comando):].strip()
            return comando, args
    return None, data


def signal_handler(sig, frame):
    logging.info("Sinal SIGINT recebido, encerrando servidor...")
    sel.close()
    os._exit(0)
    

def handle_client(conn, addr):
    logging.info(f"Cliente conectado: {addr}")
    with conn:
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                try:
                    data_decifrada = data.decode().strip()
                    comando, args = comando_digitado(data_decifrada)

                    if comando in comandos:
                        desconectar = comandos[comando](conn, addr, args)
                        if desconectar:
                            break
                    else:
                        logging.info(f"Mensagem recebida de {addr}: {data.decode()}")
                        conn.sendall(data_decifrada.encode())

                except Exception as e:
                    logging.error(f"Erro ao processar mensagem de {addr}: {e}")
                    conn.sendall(b"ERROR_PROCESSING_MESSAGE")
            except ConnectionResetError:
                logging.info(f"Cliente desconectado: {addr}")
                break
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
