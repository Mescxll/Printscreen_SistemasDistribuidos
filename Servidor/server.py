import socket
import struct
import pyperclip
from datetime import datetime
from pathlib import Path

HOST = "0.0.0.0"
PORT = 5001
PASTA_IMAGENS = Path("imagens_recebidas")

HEADER_EXT_SIZE = 4
HEADER_TAM_SIZE = 8

HEADER_TOTAL = HEADER_EXT_SIZE + HEADER_TAM_SIZE

def recv_exato(conexao: socket.socket, quantidade: int) -> bytes:
    dados = bytearray()
    while len(dados) < quantidade:
        pedaco = conexao.recv(quantidade - len(dados))
        if not pedaco:
            raise ConnectionError(
            )
        dados.extend(pedaco)
    return bytes(dados)


def receber_header(conexao: socket.socket) -> tuple[str, int]:
    header = recv_exato(conexao, HEADER_TOTAL)

    extensao_bruta = header[:HEADER_EXT_SIZE]
    tamanho_bruto = header[HEADER_EXT_SIZE:HEADER_TOTAL]

    extensao = extensao_bruta.rstrip(b"\x00").decode("ascii")

    (tamanho,) = struct.unpack(">Q", tamanho_bruto)

    return extensao, tamanho

def salvar_imagem(dados_imagem: bytes, extensao: str) -> Path:
    PASTA_IMAGENS.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    caminho = PASTA_IMAGENS / f"printscreen_{timestamp}.{extensao}"

    with open(caminho, "wb") as arquivo:
        arquivo.write(dados_imagem)

    return caminho


def atualizar_clipboard_local(caminho_arquivo: Path) -> None:
    mensagem = f"Imagem recebida e salva em: {caminho_arquivo.resolve()}"
    pyperclip.copy(mensagem)
    print(f"[clipboard local atualizado] {mensagem}")
 
 
def tratar_cliente(conexao: socket.socket, endereco) -> None:
    print(f"[+] Conexão recebida de {endereco}")
    try:
        extensao, tamanho = receber_header(conexao)
        print(f"    Extensão: .{extensao} | Tamanho esperado: {tamanho} bytes")
 
        dados_imagem = recv_exato(conexao, tamanho)
 
        caminho = salvar_imagem(dados_imagem, extensao)
        print(f"    Imagem salva em: {caminho}")
 
        atualizar_clipboard_local(caminho)
 
        conexao.sendall(b"OK\n")
 
    except ConnectionError as erro:
        print(f"    [!] Erro de conexão: {erro}")
        try:
            conexao.sendall(f"ERRO:{erro}\n".encode("utf-8"))
        except OSError:
            pass
    except Exception as erro:
        print(f"    [!] Erro inesperado: {erro}")
        try:
            conexao.sendall(f"ERRO:{erro}\n".encode("utf-8"))
        except OSError:
            pass
    finally:
        conexao.close()
        print(f"[-] Conexão com {endereco} encerrada")
 
 
def iniciar_servidor() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((HOST, PORT))
        servidor.listen()
        print(f"Servidor escutando em {HOST}:{PORT} — aguardando conexões...")
 
        while True:
            conexao, endereco = servidor.accept()
            tratar_cliente(conexao, endereco)
 
 
if __name__ == "__main__":
    try:
        iniciar_servidor()
    except KeyboardInterrupt:
        print("\nServidor encerrado manualmente (Ctrl+C).")
