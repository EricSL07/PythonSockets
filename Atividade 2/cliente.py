import socket
import logging
import signal
import sys
import struct
import os

HOST = "127.0.0.1"
PORT = 65432

def handle_sigint(sig, frame):
    logging.info("Sinal SIGINT recebido, encerrando cliente...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)

def enviar_addfile(c, nome_arquivo):
    if not os.path.exists(nome_arquivo):
        logging.error(f"Arquivo '{nome_arquivo}' não encontrado.")
        return
    
    tipo_msg = 1
    cmd_id = 1
    nome_bytes = nome_arquivo.encode("utf-8")
    tamanho_nome = len(nome_bytes)

    cabecalho = struct.pack("!BBB", tipo_msg, cmd_id, tamanho_nome)
    c.sendall(cabecalho + nome_bytes)

    tamanho_arquivo = os.path.getsize(nome_arquivo)
    tamanho_bytes = struct.pack("!I", tamanho_arquivo)
    c.sendall(tamanho_bytes)

    logging.info(f"Enviando arquivo '{nome_arquivo}' ({tamanho_arquivo} bytes)...")
    with open(nome_arquivo, "rb") as f:
        while True:
            chunk = f.read(1024)
            if not chunk:
                break
            c.sendall(chunk)
    logging.info(f"Arquivo '{nome_arquivo}' enviado com sucesso.")

def deletar_arquivo(c, nome_arquivo):
    tipo_msg = 1
    cmd_id = 2
    nome_bytes = nome_arquivo.encode("utf-8")
    tamanho_nome = len(nome_bytes)

    cabecalho = struct.pack("!BBB", tipo_msg, cmd_id, tamanho_nome)
    c.sendall(cabecalho + nome_bytes)
    logging.info(f"Solicitação de exclusão do arquivo '{nome_arquivo}' enviada.")

def get_files_list(c):
    tipo_msg = 1
    cmd_id = 3
    cabecalho = struct.pack("!BBB", tipo_msg, cmd_id, 0)
    c.sendall(cabecalho)
    logging.info("Solicitação de lista de arquivos enviada.")

def get_file(c, nome_arquivo):
    tipo_msg = 1
    cmd_id = 4
    nome_bytes = nome_arquivo.encode("utf-8")
    tamanho_nome = len(nome_bytes)

    cabecalho = struct.pack("!BBB", tipo_msg, cmd_id, tamanho_nome)
    c.sendall(cabecalho + nome_bytes)
    logging.info(f"Solicitação de download do arquivo '{nome_arquivo}' enviada.")

def receber_resposta(c):
    cabecalho_resposta = c.recv(3)
    if not cabecalho_resposta or len(cabecalho_resposta) < 3:
        logging.error("Resposta do servidor incompleta.")
        return
    
    tipo_msg, cmd_id, status = struct.unpack("!BBB", cabecalho_resposta)

    if tipo_msg == 2:
        if status == 1:
            logging.info("Resposta do servidor: Sucesso")
        elif status == 2:
            logging.error("Resposta do servidor: Falha")
        else:
            logging.error(f"Resposta do servidor: Status desconhecido ({status})")

def run_client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as c:
        c.connect((HOST, PORT))
        logging.info(f"Conectado ao servidor em {HOST}:{PORT}")

        try:
            while True:
                print("1 - ADDFILE")
                print("2 - DELETEFILE")
                print("3 - GETFILELIST")
                print("4 - GETFILE")
                print("0 - Sair")

                opcao = input("Escolha uma opção: ")

                if opcao == "1":
                    nome_arquivo = input("Digite o nome do arquivo a ser enviado: ")
                    enviar_addfile(c, nome_arquivo)
                    receber_resposta(c)

                elif opcao == "2":
                    nome_arquivo = input("Digite o nome do arquivo a ser deletado: ")
                    deletar_arquivo(c, nome_arquivo)
                    receber_resposta(c)

                elif opcao == "3":
                    get_files_list(c)
                    receber_resposta(c)

                elif opcao == "4":
                    nome_arquivo = input("Digite o nome do arquivo a ser baixado: ")
                    get_file(c, nome_arquivo)
                    receber_resposta(c)

                elif opcao == "0":
                    logging.info("Encerrando cliente...")
                    break

                else:
                    logging.warning("Opção inválida. Tente novamente.")

        except Exception as e:
            logging.error(f"Erro no cliente: {e}")
        finally:
            c.close()
            logging.info("Conexão encerrada.")

if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.info("Iniciando cliente")
    run_client()