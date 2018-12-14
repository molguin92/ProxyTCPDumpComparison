import base64
import struct
from socket import IPPROTO_TCP, SOL_SOCKET, SO_KEEPALIVE, TCP_KEEPCNT, \
    TCP_KEEPIDLE, TCP_KEEPINTVL
from socketserver import BaseRequestHandler, ThreadingTCPServer

import click

from netutils import recvmsg


def set_keepalive_linux(sock, after_idle_sec=1, interval_sec=3, max_fails=5):
    '''Set TCP keepalive on an open socket.
    It activates after 1 second (after_idle_sec) of idleness,
    then sends a keepalive ping once every 3 seconds (interval_sec),
    and closes the connection after 5 failed ping (max_fails), or 15 seconds
    '''
    sock.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
    sock.setsockopt(IPPROTO_TCP, TCP_KEEPIDLE, after_idle_sec)
    sock.setsockopt(IPPROTO_TCP, TCP_KEEPINTVL, interval_sec)
    sock.setsockopt(IPPROTO_TCP, TCP_KEEPCNT, max_fails)


# noinspection PyAttributeOutsideInit
class EchoHandler(BaseRequestHandler):
    img: bytes
    # handler for the server which simply sends an image back to the client

    IMG_PATH: str = './img.jpeg'

    def setup(self):
        set_keepalive_linux(self.request)
        with open(self.IMG_PATH, 'r') as img_f:
            self.img = base64.b32encode(img_f.read())
        self.img_len = len(self.img)

    def handle(self):
        print('Client connected:', self.client_address[0])
        while True:
            try:
                _ = recvmsg(self.request)

                # received request, now return image
                self.request.sendall(
                    struct.pack(f'>I{self.img_len}s',
                                self.img_len,
                                self.img))
            except Exception:
                print('Client disconnected:', self.client_address[0])
                return


@click.command(help='Echo listen server')
@click.argument('host', type=str, default='0.0.0.0')
@click.argument('port', type=int, default=1337)
def main(host: str, port: int):
    with ThreadingTCPServer((host, port), EchoHandler) as server:
        server.serve_forever()


if __name__ == '__main__':
    main()
