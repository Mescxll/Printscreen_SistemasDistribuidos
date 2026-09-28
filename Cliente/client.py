import io
import socket
import struct
import sys
import time
from PIL import Image, ImageGrab

PORTA_PADRAO = 5001
TAMANHO_EXTENSAO = 4

def obter_imagem_clipboard() -> bytes:
    conteudo = ImageGrab.grabclipboard()

    if conteudo is None:
        raise RuntimeError(
            "Nenhuma imagem foi encontrada na area de transferencia."
        )

    if isinstance(conteudo, list):
        if not conteudo:
            raise RuntimeError("A area de transferencia esta vazia.")

        caminho_imagem = conteudo[0]
        imagem = Image.open(caminho_imagem)
    else:
        imagem = conteudo

    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    return buffer.getvalue()


def enviar_imagem(host: str, porta: int, dados_imagem: bytes) -> None:
    extensao = b"png".ljust(TAMANHO_EXTENSAO, b"\x00")
    tamanho = struct.pack(">Q", len(dados_imagem))

    mensagem = extensao + tamanho + dados_imagem

    with socket.create_connection((host, porta), timeout=10) as conexao:
        conexao.sendall(mensagem)

        resposta = conexao.recv(1024).decode("utf-8", errors="replace")

    if resposta.startswith("OK"):
        print("Imagem enviada com sucesso.")
    else:
        raise RuntimeError(f"Resposta do servidor: {resposta.strip()}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Exemplo de uso: python client.py IP_DO_SERVIDOR [PORTA]")
        sys.exit(1)

    host = sys.argv[1]
    porta = int(sys.argv[2]) if len(sys.argv) >= 3 else PORTA_PADRAO

    try:
        try:
            ultima_imagem = obter_imagem_clipboard()
        except RuntimeError:
            ultima_imagem = None

        print("Monitorando o clipboard. Pressione Ctrl+C para encerrar.")

        while True:
            time.sleep(0.5)

            try:
                dados_imagem = obter_imagem_clipboard()
            except RuntimeError:
                continue

            if dados_imagem == ultima_imagem:
                continue

            try:
                print(f"Nova imagem: {len(dados_imagem)} bytes")
                enviar_imagem(host, porta, dados_imagem)
                ultima_imagem = dados_imagem
            except Exception as erro:
                print(f"Erro ao enviar imagem: {erro}")
                time.sleep(2)

    except KeyboardInterrupt:
        print("\nCliente encerrado.")


if __name__ == "__main__":
    main()