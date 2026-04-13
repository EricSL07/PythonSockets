import logging

import selectors
import socket
import sys
import types
import threading
import os
import signal
import struct

HOST = "127.0.0.1"
PORT = 65432
PASTA_PADRAO = "arquivos_servidor"

lock = threading.Lock()
sel = selectors.DefaultSelector()

if not os.path.exists(PASTA_PADRAO):
    os.makedirs(PASTA_PADRAO)

def receber_cabecalho(conn, n):
    data = bytearray()
    while len(data) < n:
        pacote = conn.recv(n - len(data))
        if not pacote:
            return None
        data.extend(pacote)
    return bytes(data)

def handle_sigint(sig, frame):
    logging.info("Sinal SIGINT recebido, encerrando servidor...")
    sel.close()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)

def handle_client(conn, addr):
    logging.info(f"Conexão estabelecida com {addr}")
    try:
        while True:
            cabecalho = receber_cabecalho(conn, 3)
            if not cabecalho:
                logging.info(f"Cliente {addr} desconectado")
                break

            tipo_msg, cmd_id, tamanho_nome = struct.unpack("!BBB", cabecalho)

            if tipo_msg != 1:
                logging.error(f"Tipo de mensagem inválido de {addr}")
                continue

            nome_bytes = receber_cabecalho(conn, tamanho_nome)
            nome_arquivo = nome_bytes.decode("utf-8")

            nome_arquivo = os.path.basename(nome_arquivo)

            if cmd_id == 1:  # ADDFILES
                caminho_final = os.path.join(PASTA_PADRAO, nome_arquivo)

                tamanho_bytes = receber_cabecalho(conn, 4)
                tamanho_arquivo = struct.unpack(">I", tamanho_bytes)[0]

                logging.info(f"Recebendo arquivo '{nome_arquivo}' ({tamanho_arquivo} bytes) de {addr}...")
                bytes_recebidos = 0

                with open(caminho_final, "wb") as f:
                    while bytes_recebidos < tamanho_arquivo:
                        falta = tamanho_arquivo - bytes_recebidos
                        ler_agora = min(1024, falta)
                        chunk = conn.recv(ler_agora)
                        if not chunk:
                            logging.warning(f"Conexão perdida durante o recebimento de '{nome_arquivo}' de {addr}")
                            break
                        f.write(chunk)
                        bytes_recebidos += len(chunk)
                
                logging.info(f"Arquivo '{nome_arquivo}' recebido com sucesso de {addr}.")
                resposta = struct.pack("!BBB", 2, cmd_id, 1)
                conn.sendall(resposta)

            elif cmd_id == 2:  # DELETEFILES
                caminho_final = os.path.join(PASTA_PADRAO, nome_arquivo)
                if os.path.exists(caminho_final):
                    os.remove(caminho_final)
                    logging.info(f"Arquivo '{nome_arquivo}' deletado por {addr}.")
                    resposta = struct.pack("!BBB", 2, cmd_id, 1)
                else:
                    logging.warning(f"Arquivo '{nome_arquivo}' não encontrado para exclusão por {addr}.")
                    resposta = struct.pack("!BBB", 2, cmd_id, 2)
                conn.sendall(resposta)
            
            elif cmd_id == 3:  # GETFILELIST
                arquivos = os.listdir(PASTA_PADRAO)
                lista_arquivos = ",".join(arquivos)
                resposta = struct.pack("!BBB", 2, cmd_id, 1) + lista_arquivos.encode("utf-8")
                conn.sendall(resposta)

            elif cmd_id == 4:  # GETFILE
                caminho_final = os.path.join(PASTA_PADRAO, nome_arquivo)
                if os.path.exists(caminho_final):
                    tamanho_arquivo = os.path.getsize(caminho_final)
                    resposta = struct.pack("!BBB", 2, cmd_id, 1) + struct.pack(">I", tamanho_arquivo)
                    conn.sendall(resposta)


                    with open(caminho_final, "rb") as f:
                        conteudo = f.read(1024)
                        if not conteudo:
                            logging.warning(f"Arquivo '{nome_arquivo}' está vazio para envio a {addr}.")
                            break
                        conn.sendall(conteudo)
                        
                    logging.info(f"Arquivo '{nome_arquivo}' enviado para {addr}.")

                else:
                    logging.warning(f"Arquivo '{nome_arquivo}' não encontrado para envio a {addr}.")
                    resposta = struct.pack("!BBB", 2, cmd_id, 2)
                    conn.sendall(resposta)

            else:
                logging.warning(f"Comando desconhecido (cmd_id={cmd_id}) recebido de {addr}")
                resposta = struct.pack("!BBB", 2, cmd_id, 2)
                conn.sendall(resposta)


    except Exception as e:
        logging.error(f"Erro ao lidar com cliente {addr}: {e}")
    finally:
        conn.close()
        logging.info(f"Conexão encerrada: {addr}")


def run_server():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            logging.info(f"Servidor ouvindo em {HOST}:{PORT}")

            while True:
                conn, addr = s.accept()
                logging.info(f"Nova conexão de {addr}")
                threading.Thread(target=handle_client, args=(conn, addr)).start()
    except Exception as e:
        logging.error(f"Erro no servidor: {e}")
    finally:
        sel.close()


if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.info("Iniciando servidor")
    run_server()