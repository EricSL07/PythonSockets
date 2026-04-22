"""Servidor de socket TCP para gerenciar usuários e arquivos.

Este servidor implementa um sistema de autenticação e gerenciamento de arquivos.
Cada cliente conectado é atendido por uma thread separada. O servidor suporta
comandos como CADASTRO (criar usuário), CONNECT (autenticar), PWD (diretório atual),
GETFILES (listar arquivos), ADDFILES (criar arquivo), DELETEFILES (deletar arquivo), etc.

Cada usuário tem seu próprio diretório com seus arquivos.
"""

from signal import signal
import socket
import time
import threading
import selectors
import logging
import os
import signal
import sys

# Lock para evitar conflitos ao acessar arquivos compartilhados
lock = threading.Lock()

HOST = "127.0.0.1"  # Interface localhost
PORT = 65432  # Porta para escutar conexões

# Seletor para gerenciar múltiplas conexões (não usado na implementação atual)
sel = selectors.DefaultSelector()


def cadastro_comando(conn, addr, args):
    """Registra um novo usuário no sistema.
    
    Recebe usuário e senha separados por vírgula, salva em users.txt
    e cria um diretório para o novo usuário.
    """
    logging.info(f"Comando CADASTRO recebido de {addr}")
    user, password = args.split(",")
    with lock:
        with open("users.txt", "a") as f:
            f.write(f"{user},{password}\n")
            os.mkdir(f"users/{user}")
            conn.sendall(b"USER_REGISTERED")


def connect_comando(conn, addr, args):
    """Autentica um usuário existente.
    
    Verifica se o usuário e senha estão em users.txt. Se forem válidos,
    muda o diretório de trabalho para o diretório do usuário.
    """
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
    """Encerra a conexão com o cliente.
    
    Fecha a conexão de forma graceful.
    """
    logging.info(f"Comando EXIT recebido de {addr}")
    conn.sendall(b"")
    conn.close()


def pwd_comando(conn, addr, args):
    """Retorna o diretório de trabalho atual do cliente.
    
    Envia o caminho do diretório onde o usuário está.
    """
    logging.info(f"Comando PWD recebido de {addr}")
    conn.sendall(os.getcwd().encode())


def getdirs_comando(conn, addr, args):
    """Lista todos os diretórios no diretório atual do cliente.
    
    Retorna uma string com os nomes dos diretórios separados por vírgula.
    """
    logging.info(f"Comando GETDIRS recebido de {addr}")
    dirs = [d for d in os.listdir() if os.path.isdir(d)]
    conn.sendall(",".join(dirs).encode())


def getfiles_comando(conn, addr, args):
    """Lista todos os arquivos no diretório atual do cliente.
    
    Retorna uma string com os nomes dos arquivos separados por vírgula.
    """
    logging.info(f"Comando GETFILES recebido de {addr}")
    files = [f for f in os.listdir() if os.path.isfile(f)]
    conn.sendall(",".join(files).encode())

def addfiles_comando(conn, addr, args):
    """Cria um novo arquivo com conteúdo especificado.
    
    Recebe nome e conteúdo separados por vírgula.
    """
    logging.info(f"Comando ADDFILES recebido de {addr}")
    filename, content = args.split(",", 1)
    with lock:
        with open(filename, "w") as f:
            f.write(content)
        conn.sendall(b"FILE_CREATED")

def deletefiles_comando(conn, addr, args):
    """Deleta um arquivo do diretório do cliente.
    
    Verifica se o arquivo existe antes de deletar.
    """
    logging.info(f"Comando DELETEFILES recebido de {addr}")
    filename = args.strip()
    with lock:
        if os.path.exists(filename):
            os.remove(filename)
            conn.sendall(b"FILE_DELETED")
        else:
            conn.sendall(b"FILE_NOT_FOUND")

def getfileslist_comando(conn, addr, args):
    """Lista todos os arquivos no diretório atual do cliente.
    
    Similar ao GETFILES, retorna nomes de arquivos separados por vírgula.
    """
    logging.info(f"Comando GETFILESLIST recebido de {addr}")
    files = [f for f in os.listdir() if os.path.isfile(f)]
    conn.sendall(",".join(files).encode())

def getfile_comando(conn, addr, args):
    """Lê e envia o conteúdo de um arquivo ao cliente.
    
    Verifica se o arquivo existe antes de ler seu conteúdo.
    """
    logging.info(f"Comando GETFILE recebido de {addr}")
    filename = args.strip()
    with lock:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                content = f.read()
            conn.sendall(content.encode())
        else:
            conn.sendall(b"FILE_NOT_FOUND")

# Dicionário que mapeia nomes de comandos para suas funções
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
    """Identifica qual comando foi enviado e extrai os argumentos.
    
    Verifica se a mensagem começa com algum comando conhecido.
    Se encontrar, extrai os argumentos após o comando.
    """
    for comando in comandos:
        if data.startswith(comando):
            args = data[len(comando):].strip()
            return comando, args
    return None, data

def signal_handler(sig, frame):
    """Gerencia o sinal de interrupção (Ctrl+C).
    
    Encerra o servidor de forma segura quando o usuário pressiona Ctrl+C.
    """
    logging.info("Sinal SIGINT recebido, encerrando servidor...")
    sel.close()
    os._exit(0)
    

def handle_client(conn, addr):
    """Processa as requisições de um cliente conectado.
    
    Recebe mensagens do cliente, identifica o comando e executa
    a função correspondente. Esta função roda em uma thread separada
    para cada cliente conectado.
    """
    logging.info(f"Cliente conectado: {addr}")
    with conn:
        while True:
            try:
                # Recebe dados do cliente
                data = conn.recv(1024)
                if not data:
                    break
                try:
                    # Decodifica e processa a mensagem
                    data_decifrada = data.decode().strip()
                    comando, args = comando_digitado(data_decifrada)

                    # Executa o comando se for reconhecido
                    if comando in comandos:
                        desconectar = comandos[comando](conn, addr, args)
                        if desconectar:
                            break
                    else:
                        # Se não for um comando, ecoa a mensagem
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
    """Função principal que inicia o servidor.
    
    Cria um socket, o vincula ao HOST e PORT, e fica aguardando
    conexões. Para cada cliente conectado, cria uma thread separada
    para processar suas requisições.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        logging.info(f"Servidor executando em {HOST}:{PORT}")
        # Aguarda e aceita conexões de clientes
        while True:
            conn, addr = s.accept()
            # Cria uma thread para cada cliente
            threading.Thread(target=handle_client, args=(conn, addr)).start()
            logging.info(f"Nova conexão de {addr}")

if "__main__" == __name__:
    # Configura logging para exibir hora, minuto e segundo
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.info("Iniciando servidor")

    # Registra o handler para encerrar o servidor com Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    main()
