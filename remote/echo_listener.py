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


class EchoHandler(BaseRequestHandler):
    # handler for the server which simply echoes the incoming data multiplied
    # by a certain factor in order to fake a heavy downlink connection

    MULT_FACTOR = 500

    # mult factor chosen as 500 since by default the data sent from the
    # client consists of 512 bytes. 500 x 512bytes = 256 Kb, which is a
    # reasonable size for a small image.

    def setup(self):
        set_keepalive_linux(self.request)

    def handle(self):
        print('Client connected:', self.client_address[0])
        while True:
            try:
                data = recvmsg(self.request)
                # repeat data MULT_FACTOR times and send
                data = data * self.MULT_FACTOR
                out_len = len(data)
                self.request.sendall(
                    struct.pack(f'>I{out_len}s', out_len, data))
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
