"""Servidor de transferência de arquivos com protocolo binário.

Implementa um servidor que gerencia arquivos através de um protocolo binário
com struct. Suporta operações de upload (ADDFILES), download (GETFILE),
listagem (GETFILELIST) e exclusão (DELETEFILES) de arquivos.
Cada cliente conectado é atendido por uma thread separada.
"""

import logging
import selectors
import socket
import sys
import types
import threading
import os
import signal
import struct

HOST = "127.0.0.1"  # Interface localhost
PORT = 65432  # Porta para escutar conexões
PASTA_PADRAO = "arquivos_servidor"  # Diretório onde os arquivos são armazenados

lock = threading.Lock()  # Lock para sincronização de threads
sel = selectors.DefaultSelector()  # Seletor para gerenciar múltiplas conexões

# Cria o diretório padrão se ele não existir
if not os.path.exists(PASTA_PADRAO):
    os.makedirs(PASTA_PADRAO)

def receber_cabecalho(conn, n):
    """Recebe exatamente n bytes do cliente.
    
    Continua recebendo até ter n bytes completos ou a conexão ser fechada.
    Retorna os bytes recebidos ou None se a conexão foi fechada.
    """
    data = bytearray()
    while len(data) < n:
        pacote = conn.recv(n - len(data))
        if not pacote:
            return None
        data.extend(pacote)
    return bytes(data)

def handle_sigint(sig, frame):
    """Gerencia o sinal de interrupção (Ctrl+C).
    
    Encerra o servidor de forma segura quando o usuário pressiona Ctrl+C.
    """
    logging.info("Sinal SIGINT recebido, encerrando servidor...")
    sel.close()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)

def handle_client(conn, addr):
    """Processa as requisições de um cliente conectado.
    
    Recebe mensagens do cliente em formato binário (tipo, comando, tamanho).
    Executa a operação solicitada (upload, download, listagem, exclusão)
    e envia uma resposta ao cliente. Esta função roda em uma thread separada
    para cada cliente conectado.
    """
    logging.info(f"Conexão estabelecida com {addr}")
    try:
        while True:
            # Recebe cabeçalho com 3 bytes: tipo_msg, cmd_id, tamanho_nome
            cabecalho = receber_cabecalho(conn, 3)
            if not cabecalho:
                logging.info(f"Cliente {addr} desconectado")
                break

            # Desempacota o cabeçalho
            tipo_msg, cmd_id, tamanho_nome = struct.unpack("!BBB", cabecalho)

            if tipo_msg != 1:
                logging.error(f"Tipo de mensagem inválido de {addr}")
                continue

            # Recebe o nome do arquivo com o tamanho especificado
            nome_bytes = receber_cabecalho(conn, tamanho_nome)
            nome_arquivo = nome_bytes.decode("utf-8")

            # Remove qualquer caminho do nome do arquivo por segurança
            nome_arquivo = os.path.basename(nome_arquivo)

            # COMANDO 1: ADDFILES (Upload de arquivo)
            if cmd_id == 1:
                # Constrói o caminho completo do arquivo
                caminho_final = os.path.join(PASTA_PADRAO, nome_arquivo)

                # Recebe o tamanho do arquivo (4 bytes em formato big-endian)
                tamanho_bytes = receber_cabecalho(conn, 4)
                tamanho_arquivo = struct.unpack("!I", tamanho_bytes)[0]

                logging.info(f"Recebendo arquivo '{nome_arquivo}' ({tamanho_arquivo} bytes) de {addr}...")
                bytes_recebidos = 0

                # Cria o arquivo no servidor e recebe o conteúdo em chunks
                with open(caminho_final, "wb") as f:
                    while bytes_recebidos < tamanho_arquivo:
                        falta = tamanho_arquivo - bytes_recebidos
                        ler_agora = min(1024, falta)
                        chunk = conn.recv(ler_agora)
                        if not chunk:
                            logging.warning(f"Conexão perdida durante o recebimento de '{nome_arquivo}' de {addr}")
                            resposta = struct.pack("!BBB", 2, cmd_id, 2)
                            conn.sendall(resposta)
                            break
                        f.write(chunk)
                        bytes_recebidos += len(chunk)

                logging.info(f"Arquivo '{nome_arquivo}' recebido com sucesso de {addr}.")
                # Envia resposta de sucesso (status 1)
                resposta = struct.pack("!BBB", 2, cmd_id, 1)
                conn.sendall(resposta)

            # COMANDO 2: DELETEFILES (Deletar arquivo)
            elif cmd_id == 2:
                # Constrói o caminho completo do arquivo
                caminho_final = os.path.join(PASTA_PADRAO, nome_arquivo)
                if os.path.exists(caminho_final):
                    os.remove(caminho_final)
                    logging.info(f"Arquivo '{nome_arquivo}' deletado por {addr}.")
                    # Envia resposta de sucesso
                    resposta = struct.pack("!BBB", 2, cmd_id, 1)
                else:
                    logging.warning(f"Arquivo '{nome_arquivo}' não encontrado para exclusão por {addr}.")
                    # Envia resposta de falha
                    resposta = struct.pack("!BBB", 2, cmd_id, 2)
                conn.sendall(resposta)
            
            # COMANDO 3: GETFILELIST (Listar arquivos disponíveis)
            elif cmd_id == 3:
                try:
                    # Lista todos os arquivos no diretório padrão
                    arquivos = os.listdir(PASTA_PADRAO)
                    num_arquivos = len(arquivos)
                    
                    # Cabeçalho de resposta de sucesso
                    resposta = struct.pack("!BBB", 2, cmd_id, 1)

                    # Número de arquivos (2 bytes, big-endian)
                    dados_lista = struct.pack("!H", num_arquivos)

                    # Para cada arquivo, envia tamanho do nome + nome
                    for arq in arquivos:
                        arq_bytes = arq.encode("utf-8")
                        tamanho_arq = len(arq_bytes)
                        dados_lista += struct.pack("!B", tamanho_arq) + arq_bytes
                    
                    conn.sendall(resposta + dados_lista)
                    logging.info(f"Lista de arquivos enviada para {addr}.")
                except Exception as e:
                    logging.error(f"Erro ao listar arquivos para {addr}: {e}")
                    # Envia resposta de falha
                    resposta = struct.pack("!BBB", 2, cmd_id, 2)
                    conn.sendall(resposta)

            # COMANDO 4: GETFILE (Download de arquivo)
            elif cmd_id == 4:
                # Constrói o caminho completo do arquivo
                caminho_final = os.path.join(PASTA_PADRAO, nome_arquivo)
                if os.path.exists(caminho_final):
                    # Obtém o tamanho do arquivo
                    tamanho_arquivo = os.path.getsize(caminho_final)
                    # Envia cabeçalho de sucesso + tamanho do arquivo
                    resposta = struct.pack("!BBB", 2, cmd_id, 1) + struct.pack("!I", tamanho_arquivo)
                    conn.sendall(resposta)

                    # Lê e envia o arquivo em chunks
                    with open(caminho_final, "rb") as f:
                        conteudo = f.read(1024)
                        if not conteudo:
                            logging.warning(f"Arquivo '{nome_arquivo}' está vazio para envio a {addr}.")
                            break
                        conn.sendall(conteudo)
                        
                    logging.info(f"Arquivo '{nome_arquivo}' enviado para {addr}.")

                else:
                    logging.warning(f"Arquivo '{nome_arquivo}' não encontrado para envio a {addr}.")
                    # Envia resposta de falha
                    resposta = struct.pack("!BBB", 2, cmd_id, 2)
                    conn.sendall(resposta)

            # Comando desconhecido
            else:
                logging.warning(f"Comando desconhecido (cmd_id={cmd_id}) recebido de {addr}")
                # Envia resposta de falha para comando desconhecido
                resposta = struct.pack("!BBB", 2, cmd_id, 2)
                conn.sendall(resposta)

    except Exception as e:
        logging.error(f"Erro ao lidar com cliente {addr}: {e}")
    finally:
        conn.close()
        logging.info(f"Conexão encerrada: {addr}")


def run_server():
    """Função principal que inicia o servidor.
    
    Cria um socket, o vincula ao HOST e PORT, e fica aguardando
    conexões. Para cada cliente conectado, cria uma thread separada
    para processar suas requisições.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            logging.info(f"Servidor ouvindo em {HOST}:{PORT}")

            # Aguarda e aceita conexões de clientes
            while True:
                conn, addr = s.accept()
                logging.info(f"Nova conexão de {addr}")
                # Cria uma thread para cada cliente
                threading.Thread(target=handle_client, args=(conn, addr)).start()
    except Exception as e:
        logging.error(f"Erro no servidor: {e}")
    finally:
        sel.close()


if __name__ == "__main__":
    # Configura logging para exibir hora, minuto e segundo
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.info("Iniciando servidor")
    # Inicia o servidor
    run_server()