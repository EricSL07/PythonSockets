"""Cliente para transferência de arquivos com protocolo binário.

Este cliente permite que o usuário faça upload, download, listagem e exclusão
de arquivos em um servidor remoto. Usa um protocolo binário baseado em struct
para comunicação com o servidor.
"""

import socket
import logging
import signal
import sys
import struct
import os

HOST = "127.0.0.1"  # Endereço do servidor (localhost)
PORT = 65432  # Porta para conectar ao servidor

def handle_sigint(sig, frame):
    """Gerencia o sinal de interrupção (Ctrl+C).
    
    Encerra o cliente de forma segura quando o usuário pressiona Ctrl+C.
    """
    logging.info("Sinal SIGINT recebido, encerrando cliente...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)

def enviar_addfile(c, nome_arquivo):
    """Envia um arquivo para o servidor (ADDFILES).
    
    Verifica se o arquivo existe localmente, monta o cabeçalho com nome
    e tamanho, e envia o conteúdo do arquivo em chunks.
    """
    if not os.path.exists(nome_arquivo):
        logging.error(f"Arquivo '{nome_arquivo}' não encontrado.")
        return

    # Tipo de mensagem = 1 (request), Comando = 1 (ADDFILES)
    tipo_msg = 1
    cmd_id = 1
    nome_bytes = nome_arquivo.encode("utf-8")
    tamanho_nome = len(nome_bytes)

    # Envia cabeçalho (tipo, comando, tamanho do nome) + nome do arquivo
    cabecalho = struct.pack("!BBB", tipo_msg, cmd_id, tamanho_nome)
    c.sendall(cabecalho + nome_bytes)

    # Obtém e envia o tamanho do arquivo
    tamanho_arquivo = os.path.getsize(nome_arquivo)
    tamanho_bytes = struct.pack("!I", tamanho_arquivo)
    c.sendall(tamanho_bytes)

    # Envia o arquivo em chunks de 1024 bytes
    logging.info(f"Enviando arquivo '{nome_arquivo}' ({tamanho_arquivo} bytes)...")
    with open(nome_arquivo, "rb") as f:
        while True:
            chunk = f.read(1024)
            if not chunk:
                break
            c.sendall(chunk)
    logging.info(f"Arquivo '{nome_arquivo}' enviado com sucesso.")

def deletar_arquivo(c, nome_arquivo):
    """Solicita a exclusão de um arquivo no servidor (DELETEFILES).
    
    Envia o cabeçalho e nome do arquivo a ser deletado.
    """
    # Tipo de mensagem = 1 (request), Comando = 2 (DELETEFILES)
    tipo_msg = 1
    cmd_id = 2
    nome_bytes = nome_arquivo.encode("utf-8")
    tamanho_nome = len(nome_bytes)

    # Envia cabeçalho e nome do arquivo
    cabecalho = struct.pack("!BBB", tipo_msg, cmd_id, tamanho_nome)
    c.sendall(cabecalho + nome_bytes)
    logging.info(f"Solicitação de exclusão do arquivo '{nome_arquivo}' enviada.")

def get_files_list(c):
    """Solicita a lista de arquivos disponíveis no servidor (GETFILELIST).
    
    Envia apenas o cabeçalho sem nome de arquivo (tamanho = 0).
    """
    # Tipo de mensagem = 1 (request), Comando = 3 (GETFILELIST)
    tipo_msg = 1
    cmd_id = 3
    # Cabeçalho com tamanho do nome = 0 (não há nome)
    cabecalho = struct.pack("!BBB", tipo_msg, cmd_id, 0)
    c.sendall(cabecalho)
    logging.info("Solicitação de lista de arquivos enviada.")

def get_file(c, nome_arquivo):
    """Solicita o download de um arquivo do servidor (GETFILE).
    
    Envia o cabeçalho e nome do arquivo a ser baixado.
    """
    # Tipo de mensagem = 1 (request), Comando = 4 (GETFILE)
    tipo_msg = 1
    cmd_id = 4
    nome_bytes = nome_arquivo.encode("utf-8")
    tamanho_nome = len(nome_bytes)

    # Envia cabeçalho e nome do arquivo
    cabecalho = struct.pack("!BBB", tipo_msg, cmd_id, tamanho_nome)
    c.sendall(cabecalho + nome_bytes)
    logging.info(f"Solicitação de download do arquivo '{nome_arquivo}' enviada.")

def receber_resposta_lista(c):
    """Recebe e processa a resposta da listagem de arquivos.
    
    Decodifica a resposta do servidor para o comando GETFILELIST,
    exibe o número de arquivos e suas names.
    """
    # Recebe cabeçalho da resposta (3 bytes)
    cabecalho_resposta = c.recv(3)
    if not cabecalho_resposta or len(cabecalho_resposta) < 3:
        logging.error("Resposta do servidor incompleta.")
        return

    tipo_msg, cmd_id, status = struct.unpack("!BBB", cabecalho_resposta)

    # Verifica se é resposta ao comando GETFILELIST
    if tipo_msg == 2 and cmd_id == 3:
        if status == 1:  # Sucesso
            # Recebe número de arquivos (2 bytes)
            num_arquivos_bytes = c.recv(2)
            num_arquivos = struct.unpack("!H", num_arquivos_bytes)[0]
            logging.info(f"Resposta do servidor: {num_arquivos} arquivos encontrados.")
            
            # Recebe cada arquivo: tamanho (1 byte) + nome
            arquivos = []
            for _ in range(num_arquivos):
                tamanho_nome_bytes = c.recv(1)
                tamanho_nome = struct.unpack("!B", tamanho_nome_bytes)[0]
                nome_bytes = c.recv(tamanho_nome)
                nome_arquivo = nome_bytes.decode("utf-8")
                arquivos.append(nome_arquivo)
            logging.info(f"Arquivos disponíveis: {', '.join(arquivos)}")
        elif status == 2:  # Falha
            logging.error("Resposta do servidor: Falha ao listar arquivos.")
        else:
            logging.error(f"Resposta do servidor: Status desconhecido ({status})")

def receber_resposta(c):
    """Recebe e processa a resposta do servidor para comandos simples.
    
    Decodifica o status de sucesso ou falha da operação realizada.
    Usado para ADDFILES, DELETEFILES e GETFILE.
    """
    # Recebe cabeçalho da resposta (3 bytes)
    cabecalho_resposta = c.recv(3)
    if not cabecalho_resposta or len(cabecalho_resposta) < 3:
        logging.error("Resposta do servidor incompleta.")
        return

    tipo_msg, cmd_id, status = struct.unpack("!BBB", cabecalho_resposta)

    # Verifica se é resposta (tipo_msg = 2)
    if tipo_msg == 2:
        if status == 1:  # Sucesso
            logging.info("Resposta do servidor: Sucesso")
        elif status == 2:  # Falha
            logging.error("Resposta do servidor: Falha")
        else:
            logging.error(f"Resposta do servidor: Status desconhecido ({status})")

def run_client():
    """Função principal que executa o cliente.
    
    Conecta ao servidor e exibe um menu interativo com as opções:
    ADDFILE (1), DELETEFILE (2), GETFILELIST (3), GETFILE (4).
    O usuário pode executar operações até escolher sair (0).
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as c:
        # Conecta ao servidor
        c.connect((HOST, PORT))
        logging.info(f"Conectado ao servidor em {HOST}:{PORT}")

        try:
            # Menu principal
            while True:
                print("\n--- Menu de Operações ---")
                print("1 - ADDFILE (Enviar arquivo)")
                print("2 - DELETEFILE (Deletar arquivo)")
                print("3 - GETFILELIST (Listar arquivos)")
                print("4 - GETFILE (Baixar arquivo)")
                print("0 - Sair")

                opcao = input("Escolha uma opção: ")

                # Opção 1: Enviar arquivo
                if opcao == "1":
                    nome_arquivo = input("Digite o nome do arquivo a ser enviado: ")
                    enviar_addfile(c, nome_arquivo)
                    receber_resposta(c)

                # Opção 2: Deletar arquivo
                elif opcao == "2":
                    nome_arquivo = input("Digite o nome do arquivo a ser deletado: ")
                    deletar_arquivo(c, nome_arquivo)
                    receber_resposta(c)

                # Opção 3: Listar arquivos
                elif opcao == "3":
                    get_files_list(c)
                    receber_resposta_lista(c)

                # Opção 4: Baixar arquivo
                elif opcao == "4":
                    nome_arquivo = input("Digite o nome do arquivo a ser baixado: ")
                    get_file(c, nome_arquivo)
                    receber_resposta(c)

                # Opção 0: Sair
                elif opcao == "0":
                    logging.info("Encerrando cliente...")
                    break

                # Opção inválida
                else:
                    logging.warning("Opção inválida. Tente novamente.")

        except Exception as e:
            logging.error(f"Erro no cliente: {e}")
        finally:
            c.close()
            logging.info("Conexão encerrada.")

if __name__ == "__main__":
    # Configura logging para exibir hora, minuto e segundo
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.info("Iniciando cliente")
    # Inicia o cliente
    run_client()