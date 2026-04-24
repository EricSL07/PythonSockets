# PythonSockets

Repositório de atividades práticas com **sockets TCP em Python**, explorando comunicação cliente-servidor, threads, protocolos binários e gerenciamento de arquivos.

---

## Estrutura do Repositório

```
PythonSockets/
├── Atividade 1/        # Servidor com autenticação de usuários e comandos de texto
│   ├── server.py
│   ├── cliente.py
│   └── users.txt
├── Atividade 2/        # Servidor de transferência de arquivos com protocolo binário
│   ├── server.py
│   ├── cliente.py
│   └── arquivos_servidor/
└── README.md
```

---

## Atividade 1 — Servidor com Autenticação e Gerenciamento de Arquivos

Um servidor TCP multi-thread que autentica usuários e permite o gerenciamento de arquivos por meio de comandos de texto.

### Funcionalidades

| Comando        | Descrição                                            | Uso                          |
|----------------|------------------------------------------------------|------------------------------|
| `CADASTRO`     | Registra um novo usuário e cria seu diretório        | `CADASTRO usuario,senha`     |
| `CONNECT`      | Autentica um usuário existente                       | `CONNECT usuario,senha`      |
| `EXIT`         | Encerra a conexão com o servidor                     | `EXIT`                       |
| `PWD`          | Retorna o diretório de trabalho atual                | `PWD`                        |
| `GETDIRS`      | Lista os diretórios no diretório atual               | `GETDIRS`                    |
| `GETFILES`     | Lista os arquivos no diretório atual                 | `GETFILES`                   |
| `ADDFILES`     | Cria um novo arquivo com conteúdo                    | `ADDFILES nome.txt,conteudo` |
| `DELETEFILES`  | Deleta um arquivo do diretório do usuário            | `DELETEFILES nome.txt`       |
| `GETFILESLIST` | Lista arquivos (similar ao GETFILES)                 | `GETFILESLIST`               |
| `GETFILE`      | Lê e retorna o conteúdo de um arquivo                | `GETFILE nome.txt`           |

### Como executar

1. Inicie o servidor:
   ```bash
   cd "Atividade 1"
   python server.py
   ```

2. Em outro terminal, inicie o cliente:
   ```bash
   cd "Atividade 1"
   python cliente.py
   ```

3. Digite os comandos no prompt do cliente, por exemplo:
   ```
   CADASTRO alice,senha123
   CONNECT alice,senha123
   ADDFILES notas.txt,Conteudo do arquivo
   GETFILES
   ```

---

## Atividade 2 — Transferência de Arquivos com Protocolo Binário

Um servidor TCP multi-thread para upload, download, listagem e exclusão de arquivos, utilizando um **protocolo binário** baseado em `struct` para comunicação eficiente.

### Protocolo

Cada mensagem enviada pelo cliente segue o formato:

| Campo          | Tamanho  | Descrição                              |
|----------------|----------|----------------------------------------|
| `tipo_msg`     | 1 byte   | Tipo da mensagem (`1` = request)       |
| `cmd_id`       | 1 byte   | ID do comando (1–4)                    |
| `tamanho_nome` | 1 byte   | Tamanho do nome do arquivo em bytes    |
| `nome_arquivo` | variável | Nome do arquivo (UTF-8)                |

Para upload (ADDFILES), o nome é seguido por 4 bytes com o tamanho do arquivo e então o conteúdo binário.

### Comandos disponíveis

| ID | Operação        | Descrição                                      |
|----|-----------------|------------------------------------------------|
| 1  | `ADDFILES`      | Faz upload de um arquivo para o servidor       |
| 2  | `DELETEFILES`   | Deleta um arquivo do servidor                  |
| 3  | `GETFILELIST`   | Lista os arquivos disponíveis no servidor      |
| 4  | `GETFILE`       | Faz download de um arquivo do servidor         |

### Como executar

1. Inicie o servidor:
   ```bash
   cd "Atividade 2"
   python server.py
   ```

2. Em outro terminal, inicie o cliente:
   ```bash
   cd "Atividade 2"
   python cliente.py
   ```

3. Utilize o menu interativo para escolher a operação desejada:
   ```
   --- Menu de Operações ---
   1 - ADDFILE (Enviar arquivo)
   2 - DELETEFILE (Deletar arquivo)
   3 - GETFILELIST (Listar arquivos)
   4 - GETFILE (Baixar arquivo)
   0 - Sair
   ```

---

## Requisitos

- Python 3.x
- Módulos da biblioteca padrão: `socket`, `threading`, `struct`, `logging`, `os`, `signal`

Não são necessárias dependências externas.

---

## Referências

- https://pt.python-3.com/?p=166
- https://www.datacamp.com/pt/tutorial/a-complete-guide-to-socket-programming-in-python
- https://docs.python.org/pt-br/3/howto/sockets.html
- https://dev.to/leapcell/from-scratch-building-http2-and-websocket-with-raw-python-sockets-11lp
- https://docs.python.org/3/library/struct.html
- https://realpython.com/python-bytearray/
