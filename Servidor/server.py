import io
import platform
import socket
import struct
import subprocess
from datetime import datetime
from pathlib import Path

from PIL import Image

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
            # Conexão foi fechada pelo cliente antes de terminar o envio
            raise ConnectionError(
                "Conexão encerrada pelo cliente antes de receber todos os dados."
            )
        dados.extend(pedaco)
    return bytes(dados)


def receber_header(conexao: socket.socket) -> tuple[str, int]:
    """Lê e decodifica o header fixo: extensão do arquivo + tamanho em bytes."""
    header = recv_exato(conexao, HEADER_TOTAL)

    extensao_bruta = header[:HEADER_EXT_SIZE]
    tamanho_bruto = header[HEADER_EXT_SIZE:HEADER_TOTAL]

    extensao = extensao_bruta.rstrip(b"\x00").decode("ascii")

    (tamanho,) = struct.unpack(">Q", tamanho_bruto)

    return extensao, tamanho


def salvar_imagem(dados_imagem: bytes, extensao: str) -> Path:
    """Salva os bytes da imagem em disco com um nome único baseado em timestamp."""
    PASTA_IMAGENS.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    caminho = PASTA_IMAGENS / f"printscreen_{timestamp}.{extensao}"

    with open(caminho, "wb") as arquivo:
        arquivo.write(dados_imagem)

    return caminho


def copiar_imagem_para_clipboard(caminho_imagem: Path) -> None:
    sistema = platform.system()

    if sistema == "Windows":
        _copiar_clipboard_windows(caminho_imagem)
    elif sistema == "Linux":
        _copiar_clipboard_linux(caminho_imagem)
    else:
        raise RuntimeError(f"Sistema operacional não suportado: {sistema}")


def _copiar_clipboard_windows(caminho_imagem: Path) -> None:
    import win32clipboard

    imagem = Image.open(caminho_imagem)
    buffer = io.BytesIO()
    imagem.convert("RGB").save(buffer, "BMP")
    dados_dib = buffer.getvalue()[14:]
    buffer.close()

    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dados_dib)
    finally:
        win32clipboard.CloseClipboard()


def _copiar_clipboard_linux(caminho_imagem: Path) -> None:
    resultado = subprocess.run(
        [
            "xclip",
            "-selection",
            "clipboard",
            "-t",
            "image/png",
            "-i",
            str(caminho_imagem),
        ],
        capture_output=True,
    )
    if resultado.returncode != 0:
        raise RuntimeError(
            f"Falha ao copiar imagem via xclip: {resultado.stderr.decode(errors='replace')}."
        )


def atualizar_clipboard_local(caminho_arquivo: Path) -> None:
    copiar_imagem_para_clipboard(caminho_arquivo)
    print(f"[clipboard local atualizado com a imagem] {caminho_arquivo.resolve()}")


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
